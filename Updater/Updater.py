from zipfile import ZipFile
import subprocess

def main():
    print(Constants.UpdaterLaunched)
    with ZipFile('BeyondChaos.zip', 'r') as zipObj:
       print(Constants.UpdaterUnzipping)
       # Extract all the contents of zip file in different directory
       zipObj.extractall()
       #wait 3 seconds
       time.sleep(3)
       print(Constants.UpdaterCompleted)
       print(Constants.UpdaterClosing)
       subprocess.run("BeyondChaos.exe", shell=True)
       #wait 3 seconds
       time.sleep(3)
       SystemExit();

if __name__ == '__main__':
   main()