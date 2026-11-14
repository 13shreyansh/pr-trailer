"""A bounded scratch volume for untrusted test writes, separate from source and credentials."""
import fcntl
from pathlib import Path
import os
import subprocess
import threading
ROOT=Path(__file__).resolve().parents[1]
_lock=threading.Lock()

def volume():
 folder=ROOT/'var/scratch-volume';mount=folder/'mount';image=folder/'scratch.sparseimage';folder.mkdir(parents=True,exist_ok=True);mount.mkdir(exist_ok=True)
 with _lock,(folder/'mount.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  if not os.path.ismount(mount):
   if not image.exists():subprocess.run(['/usr/bin/hdiutil','create','-size','512m','-fs','APFS','-type','SPARSE','-volname','TietoScratch','-o',str(image)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   subprocess.run(['/usr/bin/hdiutil','attach',str(image),'-nobrowse','-mountpoint',str(mount),'-owners','off','-noverify'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 return mount
