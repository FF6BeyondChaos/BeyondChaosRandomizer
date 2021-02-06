
from zipfile import ZipFile

def main():
    with ZipFile('beyondchaos_ex.zip', 'r') as zipObj:
       # Extract all the contents of zip file in different directory
       zipObj.extractall()

if __name__ == '__main__':
   main()