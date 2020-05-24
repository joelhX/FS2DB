import socket
import os
import time
import hashlib
import json
import queue
import pathlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading


exclude_filename = []
exclude_dir = [".svn", ".git"]
exclude_ext = ["rev", "log", "pdb", "obj", "gitignore"]

info_FS=["","",""]
info_DB=["","",""]
info_full=info_FS+info_DB

class PackageManager(FileSystemEventHandler):
	def __init__(self, path):
		self.filename = {"FileList": "filelist.json", "DB": "filelistDB.json"}
		self.path = path
		self.FileList = dict()
		self.DB = dict()
		self.q = queue.Queue()
		self.LoadFileList()
		self.sock = socket.socket(socket.AF_INET,  socket.SOCK_DGRAM)
		self.sock.bind(('127.0.0.1', 33456))
		#for windows 10 and python 3.9(supprot U D S)
		#self.sock = socket.socket(socket.AF_UNIX,  socket.SOCK_DGRAM)
		#self.sock.bind("./uds")
		t = threading.Thread(target=self.UpdateDBList)
		t.daemon = True
		t.start()

	def LoadFileList(self):
		try:
			with open(self.filename["DB"], "r", encoding="utf8") as f:
				self.DB = json.load(f)
				print("Load "+self.filename["DB"]+":"+str(len(self.DB))+" infos")
		except:
			print("Load "+self.filename["DB"]+":"+str(len(self.DB))+" infos")

		try:
			with open(self.filename["FileList"], "r", encoding="utf8") as f:
				self.FileList = json.load(f)
				print("Load "+self.filename["FileList"] +":"+str(len(self.FileList))+" files")
		except:
			self.CreateFileList()

	def CreateFileList(self):
		for root, dirs, files in os.walk(self.path):
			dirs[:] = [d for d in dirs if d not in exclude_dir]
			for file in [f for f in files if f.split(".")[-1] not in exclude_ext]:
				fullpath = os.path.join(root, file)
				relative_path = os.path.relpath(fullpath, self.path).replace("\\", "/")
				hash = hashlib.md5()
				with open(fullpath, "rb") as f:
					hash.update(f.read())
				self.FileList[relative_path] = [hash.hexdigest(), os.stat(fullpath).st_mtime, os.stat(fullpath).st_size]+self.DB.get(relative_path, info_DB)
		for k in [k for k in self.DB.keys() if k not in self.FileList.keys()]:
			if(self.DB[3]!=""):
				self.FileList[k] = info_FS+self.DB.get(k,info_DB)
		with open(self.filename["FileList"], "w", encoding="utf8") as f:
			json.dump(self.FileList, f, ensure_ascii=False,sort_keys=True)
		print("Make "+self.filename["FileList"]+":"+str(len(self.FileList)))

	def UpdateDBList(self):
		while True:
			data = self.sock.recv(65536)  # buffer size is 1024 bytes
			changes = json.loads(data)
			self.DB.update(changes)
			for k, v in changes.items():
				self.FileList[k][len(info_FS):] = v
			with open(self.filename["FileList"], "w", encoding="utf8") as f:
				json.dump(self.FileList, f, ensure_ascii=False,sort_keys=True)
				print("Make "+self.filename["FileList"]+":"+str(len(self.FileList)))
			
			with open(self.filename["DB"], "w", encoding="utf8") as f:
				json.dump(self.DB, f, ensure_ascii=False,sort_keys=True)
				print("Update "+self.filename["DB"]+" : "+str(len(changes))+" files")

	def UpdateFSListbyQ(self):
		changed = 0
		lastupdatepath = ""
		while self.q.empty() == False:
			fullpath, remove = self.q.get()
			path=pathlib.Path(fullpath)
			if path.suffix in exclude_ext or len(set(path.parts).intersection(set(exclude_dir)))!=0:
				continue
			relative_path = os.path.relpath(fullpath, self.path)
			if(lastupdatepath == fullpath):
				continue
			else:
				lastupdatepath = fullpath
				
				changed = changed+1
				if(remove):
					temp=self.FileList.get(relative_path,info_full)
					if(temp[0]!="" and temp[-1]!=""):
						self.FileList[relative_path]=info_FS+self.DB.get(relative_path, info_DB)
					if(temp[0]!="" and temp[-1]==""):
						del self.FileList[relative_path]
			
					for dk in [f for f in self.FileList.keys() if relative_path+"/" in f]:
						temp=self.FileList.get(dk,info_full)
						if(temp[-1]!=""):
							self.FileList[dk]=info_FS+self.DB.get(dk,info_DB)
						else:
							del self.FileList[dk]
				else:
					with open(fullpath, "rb") as f:
						hash = hashlib.md5()
						hash.update(f.read())
						self.FileList[relative_path] = [hash.hexdigest(), os.stat(fullpath).st_mtime, os.stat(fullpath).st_size]+self.DB.get(relative_path, info_DB)

		if(changed != 0):
			print("Update "+self.filename["FileList"]+" : "+str(changed)+" files")
			with open(self.filename["FileList"], "w", encoding="utf8") as f:
				json.dump(self.FileList, f, ensure_ascii=False,sort_keys=True)

	def on_created(self, event):
		if event.is_directory == False:
			self.q.put([event.src_path.replace("\\", "/"), False])

	def on_modified(self, event):
		if event.is_directory == False:
			self.q.put([event.src_path.replace("\\", "/"), False])

	def on_deleted(self, event):
		if event.is_directory == False:
			self.q.put([event.src_path.replace("\\", "/"), True])

	def Watching(self):
		observer = Observer()
		observer.schedule(self, self.path, recursive=True)
		observer.start()
		try:
			while True:
				self.UpdateFSListbyQ()
				time.sleep(5)
		except:
			observer.stop()
			print("Break < Ctrl+C")
		
		observer.join()


if __name__ == '__main__':
	path = "C:/GitHub/DC"
	pm = PackageManager(path)
	pm.Watching()
