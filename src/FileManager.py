from __future__ import annotations
from typing import Union
from typing import Self
import sys

import subprocess

## Python file management:
from pathlib import Path
import shutil
import os

import json
import time


## This class represents an actual file, adding meta information stored in a .json file and operations, integrating it into a project structure.
class File():
    def __init__(self, id: str, parent: Folder):
        self.id: str = id
        self.path: str = parent.path + parent.id + '/'
        self.parent: Folder = parent
        self.type: str = 'file'
        # self.code = None

        self.cleanUp: bool = False
        self.protected: bool = False
        self.active: str = None

    ## Marks this file to be removed, when the "clean" function of the parent folder is executed.
    def trash(self):
        if not self.cleanUp:
            if not self.protected:
                self.cleanUp = True
                self.parent.save()
            else: 
                print(F'    -> cannot trash protected file {self.id}')
        return self
        
    ## Removes the cleanup mark from this file.
    def keep(self):
        if self.cleanUp:
            self.cleanUp = False
            self.parent.save()
        return self

    ## Marks this file as protected, so it can not be moved or removed via any function belonging to this tool.
    def protect(self):
        if not self.protected:
            self.protected = True
            self.parent.save()
        return self

    ## Removes the protected mark from this file.
    def unprotect(self):
        if self.protected:
            self.protected = False
            self.parent.save()
        return self

    ## ?
    def activate(self, code: str):
        if not self.active:
            self.active = code
            self.parent.save()
        return self
    
    ## ?
    def deactivate(self):
        if self.active:
            self.active = None
            self.parent.save()
        return self

    ## Uses a given list of strings and writes to the actual file. Only overwrites existing files, if the overwrite option is set to true.
    def write(self, code: list[str], overwrite: bool = False):
        code = "\n".join(code)

        ## check if file exists
        file = self.path + self.id
        if  Path(file).exists() and not overwrite:
            print(F'    -> File {file} already exists. Not overwriting.')
        else:
            with open(file, "w") as f:
                f.write(code)
        return self


## This class represents an actual folder, adding meta information stored in a .json file and operations, integrating it into a larger project structure or making it the head directory of a project.
class Folder():
    def __init__(self, id: str, path: str):
        self.id = id
        self.path = path
        self.type: str = 'folder'
        self.cleanUp: bool = False
        self.protected: bool = False
        self.active: bool = False

        self.tag: int = 0
        self.value: int = 0
        self.value2: int = 0
        self.value3: float = 0
        self.value4: float = 0

        self.subFolders: list[Folder] = []
        self.files: list[File] = []

    ## Convert this folder into a dict, ready to be stored in a .json file.
    def to_dict(self) -> dict:
        subFolderIDs = []
        for folder in self.subFolders:
            subFolderIDs.append(folder.id)

        return {
            "id": self.id,
            "path": self.path,
            "type": self.type,
            "cleanUp": self.cleanUp,
            "protected": self.protected,
            "active": self.active,
            "tag": self.tag,
            "value": self.value,
            "value2": self.value2,
            "value3": self.value3,
            "value4": self.value4,
            "subFolderIDs": subFolderIDs,
            "files": [
                {
                    "id": f.id,
                    "type": f.type,
                    "cleanUp": f.cleanUp,
                    "protected": f.protected,
                    "active": f.active
                }
                for f in self.files
            ]
        }

    ## Retrieve a folder from a given dict, loaded from a .json file.
    @staticmethod
    def from_dict(cls, d: dict, update: bool = False) -> Self:
        args = {"id": d["id"], "path": d["path"]}
        folder = cls(**args) #Folder(id=d["id"], path=d["path"])
        folder.type = d["type"]
        folder.cleanUp = d["cleanUp"]
        folder.protected = d.get("protected", False)
        folder.active = d.get("active", False)
        folder.tag = d.get("tag", '')
        folder.value = d.get("value", 0)
        folder.value2 = d.get("value2", 0)
        folder.value3 = d.get("value3", 0)
        folder.value4 = d.get("value4", 0)

        report = False

        if report: print(F'{folder.path + folder.id} | Loading subFolderIDs')
        subFolderIDs=list(d.get("subFolderIDs", []))

        ## Load all subfolders
        path = folder.path + folder.id + '/'
        for folderID in subFolderIDs:
            if report: print(F'{folder.path + folder.id} | subfolder: {folderID}')
            if report: print(F'{folder.path + folder.id} | -> looking for {path + folderID}')
            if (Path(path + folderID).exists and Path(path + folderID).is_dir()):
                if report: print(F'{folder.path + folder.id} |     -> found!')
                folder.subFolders.append(Folder.load(folderID, path, update, False))
            else:
                if not update: raise FileNotFoundError(F'No valid folder found with path {path + folderID}')

        ## Load all files
        if report: print(F'{folder.path + folder.id} || Loading files')
        files = list(d.get("files", []))
        for file in files:
            fileID = file["id"]

            if report: print(F'{folder.path + folder.id} || file: {fileID}')
            if report: print(F'{folder.path + folder.id} || -> looking for {path + fileID}')

            if (Path(path + fileID).exists and Path(path + fileID).is_file()):
                if report: print(F'{folder.path + folder.id} ||     -> found!')
                newFile = File(fileID, folder)
                newFile.type = file["type"]
                newFile.cleanUp = file["cleanUp"]
                newFile.protected = file["protected"]
                newFile.active = file["active"]
                if report: print(F'{folder.path + folder.id} ||         -> added {newFile.id}')
                folder.files.append(newFile)
            else:
                if not update: raise FileNotFoundError(F'No valid file found with path {path + fileID}')


        
        ## Going through all elements in folder, and checking if allready registered
        if report: print(F'{folder.path + folder.id} ||| Checking folder content')
        for item in Path(folder.path + folder.id).iterdir():
            if item.is_file():
                if report: print(F'{folder.path + folder.id} ||| -> File: {item.name}')
                if item.name == (folder.id + '.json'):
                    if report: print(F'{folder.path + folder.id} |||   -> is folders JSON file')
                else:
                    found = False
                    for file in folder.files:
                        if file.id == item.name:
                            if report: print(F'{folder.path + folder.id} |||     -> allready registered')
                            found = True
                    if not found:
                        if report: print(F'{folder.path + folder.id} |||     -> not registered')
                        if update:
                            newFile = File(item.name, folder)
                            ## protect unknown files
                            newFile.protected = True
                            folder.files.append(newFile)
                            folder.save()
                        else:
                            raise FileExistsError(F'Unregistered file called {item.name} found at {folder.path + folder.id}')


            elif item.is_dir():
                if report: print(F'{folder.path + folder.id} ||| -> Folder: {item.name}')
                found = False
                for subFolder in folder.subFolders:
                    if subFolder.id == item.name:
                        if report: print(F'{folder.path + folder.id} |||     -> allready registered')
                        found = True
                if not found:
                    if report: print(F'{folder.path + folder.id} |||     -> not registered')
                    if update:
                        newFolder = Folder.load(item.name, folder.path + folder.id + '/', update, False)
                        newFolder.protect()
                        folder.subFolders.append(newFolder)
                    else:
                        raise FileExistsError(F'Unregistered folder called {item.name} found at {folder.path + folder.id}')

        if report: print(F'{folder.path + folder.id} | Returning folder')
        return folder

    ## Saves this folder to a .json file.
    def save(self, overwrite: bool = True, report: bool = False, incremental = False, warn: bool = True):
        if report:
            print(F'ProjectManager: saving project {self.path + self.id}')
        if Path(self.path + self.id + '/' + self.id + '.json').exists() and not overwrite:
            if warn:
                print(F'ProjectManager: Cannot save project {self.path + self.id}, file allready exists')
            else:
                raise FileExistsError(F'ProjectManager: Cannot save project {self.path + self.id}, file allready exists')
        json_file = Path(self.path + self.id + '/' + self.id + '.json')
        with json_file.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        if incremental:
            for folder in self.subFolders:
                folder.save(overwrite, report, True)
        return self

    ## Loads and creates a folder from a given .json file.
    @classmethod
    def load(cls, id: str, path: str, update: bool = False, report: bool = True) -> Self:
        folder = path + id
        json_file = Path(path + id + '/' + id + '.json')

        if report:
            print(F'ProjectManager: opening {folder}')
            #print(F'cls for {id} is: {cls.__name__}') 

        ## check if file exists
        if Path(folder).exists():
            if not json_file.exists():
                if not update:
                    raise FileNotFoundError(F'No valid JSON file found for loading existing project folder {path + id}.')
                else:
                    if report: print("    -> No JSON found, creating folder")
                    newFolder = cls(id, path)
                    newFolder.save()
                    return newFolder
            else:
                if report: print("    -> JSON found, loading project")
                ## check if loaded project is corresponding to actual folder and file structure? -> update?
                
                with json_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    instance = cls.from_dict(cls, data, update)
                return instance
        else:
            if report: print("    -> Projectfolder does not exists, creating new.")
            Path(folder).mkdir(parents=True, exist_ok=True)
            newFolder = cls(id, path)
            newFolder.save()
            return newFolder

    ## Marks this folder to be removed, when the "clean" function of the parent folder is executed and the folder does not contain any subfolders or files, that are not marked as trash.
    ## The incremental options also marks all contained subfolders and files as trash.
    def trash(self, incremental: bool = False):
        if not self.protected:
            self.cleanUp = True
            if incremental:
                for folder in self.subFolders:
                    folder.trash(incremental)
                for file in self.files:
                    file.trash()
        else: 
            print(F'    -> cannot trash protected folder {self.path + self.id}')
        ## ?
        self.save()
        return self

    ## Removes the cleanup mark from this folder.
    def keep(self, incremental: bool = False):
        self.cleanUp = False
        if incremental:
            for folder in self.subFolders:
                folder.keep(incremental)
            for file in self.files:
                file.keep()
        self.save()
        return self

    ## Marks this folder as protected, so it can not be moved or removed via any function belonging to this tool.
    def protect(self, incremental: bool = False):
        self.protected = True
        if incremental:
            for folder in self.subFolders:
                folder.protect(incremental)
            for file in self.files:
                file.protect()
        self.save()
        return self

    ## Removes the protected mark from this folder.
    def unprotect(self, incremental: bool = False):
        self.protected = False
        if incremental:
            for folder in self.subFolders:
                folder.unprotect(incremental)
            for file in self.files:
                file.unprotect()
        self.save()
        return self

    ## Checks if this folder is protected or conains any other file or folder, that is.
    def checkProtected(self, update: bool = False):
        if self.protected:
            return True
        for file in self.files:
            if file.protected:
                if update:
                    self.protected = True
                    self.save()
                return True

        for folder in self.subFolders:
            if folder.checkProtected(update):
                if update:
                    self.protected = True
                    self.save()
                return True
        return False

    ## Loads an existing folder or creates a new one, if none was found.
    def openFolder(self, id: str, create: bool = True):
        folder = None
        for f in self.subFolders:
            if f.id == id:
                folder = f
        if folder == None:
            if create:
                path = self.path + self.id + '/'
                folder = Folder(id, path)
                Path(path + id).mkdir(parents=True, exist_ok=True)
                self.subFolders.append(folder)
                folder.save()
                self.save()
            else:
                raise FileNotFoundError(F'    -> cannot open folder {self.path + self.id + '/' + id}, it does not exist')
        return folder

    ## Loads an existing file or creates a new one, if none was found. No actual new file is created, until the files "write" function is used.
    def openFile(self, id: str, create: bool = True):
        for file in self.files:
            if file.id == id:
                return file
        if create:
            #print(F'-> create new file called {id}')
            file = File(id, self)
            self.files.append(file)
            self.save()
            return file
        else:   
            raise FileNotFoundError(F'Cannot open file at {self.path + self.id + '/' + id}, it does not exist')

    ## Returns, if this folder cotains a given subfolder. Also searches in all subfolders, if the corresponding option is set to true.
    def hasFolder(self, folder: Union[Folder, str], searchSubFolders: bool = False):
        for subFolder in self.subFolders:
            if isinstance(folder, Folder):
                if subFolder == folder:
                    return True
            else:
                if subFolder.id == folder:
                    return True
            if searchSubFolders and subFolder.hasFolder(folder, True):
                return True
        return False
    
    ## ?
    def getFolder(self, id: str):
        for folder in self.subFolders:
            if folder.id == id:
                return folder
        return False

    ## Returns, if this folder cotains a given file. Also searches in all subfolders, if the corresponding option is set to true.
    def hasFile(self, file: Union[File, str], searchSubFolders: bool = False):
        for ownFile in self.files:
            if isinstance(file, File):
                if file == ownFile:
                    return True
            else:
                if file == ownFile.id:
                    return True
        if searchSubFolders:
            for folder in self.subFolders:
                if folder.hasFile(file):
                    return True
        return False

    ## ?
    def getFile(self, id: str):
        for file in self.files:
            if file.id == id:
                return file
        return False

    ## Removes a given folder, if the folder is actually a subfolder of this folder, is not protected and does not contaion any protected subfolders or files.
    def removeFolder(self, folder: Folder):
        if not self.hasFolder(folder):
            print(F'ProjectManager: cannot remove folder {folder.id} from {self.path + self.id}, it is not part of this folder')
        else:
            if folder.protected:
                raise PermissionError(F'ProjectManager: cannot remove folder {folder.id} from {self.path + self.id}, folder is protected')
            else:
                if folder.checkProtected():
                    raise PermissionError(F'ProjectManager: cannot remove folder {folder.id} from {self.path + self.id}, folder contains protected fileds or subfolders')
                else:
                    shutil.rmtree(self.path + self.id + '/' + folder.id, ignore_errors=True)
                    self.subFolders.remove(folder)
                    self.save()

    ## Removes a given file, if the file is actually contained in this folder and not protected.
    def removeFile(self, file: File):
        if not self.hasFile(file):
            print(F'ProjectManager: cannot remove file {file.id} from {self.path + self.id}, it is not part of this folder')
        else:
            if file.protected:
                raise PermissionError(F'ProjectManager: cannot remove file {file.id} from {self.path + self.id}, file is protected')
            else:
                path = Path(self.path + self.id + '/' + file.id)
                if path.exists() and path.is_file():
                    path.unlink()
                self.files.remove(file)
                self.save()
    

    ## ?
    def moveFolder(self, id: str):
        raise NotImplementedError()

    ## ?
    def copyFolder(self, id: str):
        raise NotImplementedError()
    

    ## ?
    def moveFile(self, file: File):
        ## Move/rename
        #moved = root / "moved_example.txt"
        #shutil.move(str(file_path), str(moved))   # accepts str or Path; str is safest for older Python
        raise NotImplementedError()

    ## ?
    def copyFile(self, file: File):
        ## Copy (file or tree)
        #copy_dest = root / "copy_example.txt"
        #shutil.copy2(moved, copy_dest)            # preserves metadata where possible
        raise NotImplementedError()
    

    ## Goes through this and all subfolders and removes every file and subfolder, that is not protected and marked to be cleaned up.
    ## When the update option is set to true, folders that are not protected and empty are also removed.
    def clean(self, update: bool = False, report: bool = False):
        if report: 
            print(F'ProjectManager: cleaning Folder {self.path + self.id}')
        if update and not self.protected:
            self.cleanUp = True
        removableFiles = []
        for file in self.files:
            if file.cleanUp and not file.protected:
                removableFiles.append(file)
            else:
                if update:
                    self.cleanUp = False
        for file in removableFiles:
                self.removeFile(file)
        removableFolders = []
        for folder in self.subFolders:
            folder.clean(update, report)
            if folder.cleanUp and not folder.protected:
                removableFolders.append(folder)
            else: 
                if update:
                    self.cleanUp = False
        for folder in removableFolders:
            self.removeFolder(folder)

        self.save()
        return self
          
    ## Displays all contents of this folder and optionally all subfolders.
    def display(self, displaySubfolders: bool = True, tabs: int = 0):
        #print('\t' * tabs + F'Folder: {self.path + self.id}')
        empty = False
        if len(self.files) == 0 and len(self.subFolders) == 0:
            empty = True

        if tabs == 0:
            print(F'ProjectManager: displaying Folder {self.path + self.id} ({self.__class__.__name__})')
            if empty:
                print(F' -> is empty')
            else: 
                print()

        if not empty:
            print('\t' * (tabs) + F'          | cleanUp | protected | active | id')

            if len(self.files) > 0:
                for file in self.files:
                    cleanUp = 'n'
                    if file.cleanUp:
                        cleanUp = 'y'
                    protected = 'n'
                    if file.protected:
                        protected = 'y'
                    active = 'n'
                    if not file.active == None:
                        active = 'y'
                    print('\t' * (tabs) + ' - File   | ' + F'{cleanUp}       | {protected}         | {active}      | {file.id}')
                
            if len(self.subFolders) > 0:
                for folder in self.subFolders:
                    cleanUp = 'n'
                    if folder.cleanUp:
                        cleanUp = 'y'
                    protected = 'n'
                    if folder.protected:
                        protected = 'y'
                    active = 'n'
                    if folder.active:
                        active = 'y'
                    print('\t' * (tabs) + ' - Folder | ' + F'{cleanUp}       | {protected}         | {active}      | {folder.id}', end = '')
                    if len(folder.subFolders) == 0 and len(folder.files) == 0:
                        print(' (empty)')
                    else:
                        if displaySubfolders:
                            print()
                            print('\t' * (tabs + 5) + F' -------------')
                            folder.display(True, tabs + 5)
                            print('\t' * (tabs + 5) + F' -------------')
                        else:
                            print(F' ({len(folder.subFolders)} subfolders, {len(folder.files)} files)')
        if tabs == 0:
            print()
        return self

    ## ?
    def createExecuteShellScript(self):
        if self.hasFile('execute.sh'):
            self.removeFile(self.hasFile('execute.sh'))
        
        code = []
        for file in self.files:
            if not file.active == None:
                code.append(file.active)

        if len(code) > 0:
            shellscript = ShellScript('execute.sh', self)
            shellscript.write(code, True)
            self.files.append(shellscript)

        #self.save()
        return self

    ## ?
    def activate(self):
        self.active = True
        self.save()
        return self
    
    ## ?
    def deactivate(self):
        self.active = False
        self.save()
        return self

    ## ?
    def execute(self):
        ## ?
        raise NotImplementedError()

    ## ?
    def results(self):
        ## ?
        raise NotImplementedError()


    ## Removes this folder, if it is not protected and does not contaion any subfolder or file, that is protected
    def delete(self):
        print(F'ProjectManager: removing {self.path + self.id}')
        if self.protected:
            raise PermissionError(F'ProjectManager: cannot remove folder {self. path + self.id}, it is protected')
        if self.checkProtected():
            raise PermissionError(F'ProjectManager: cannot remove folder {self. path + self.id}, it contains protected files or subfolders')
        shutil.rmtree(self.path + self.id, ignore_errors=True)



## ?
class SpinalHDLFile(File):
    def __init__(self, id: str, parent: Folder, includeFormal: bool = False, verilogPath: str = None, generateVHDL: bool = False):
        super().__init__(id + '.scala', parent)
        self.type = 'SpinalHDLFile'
        self.toplevel = id
        self.verilogPath = verilogPath
        self.includeFormal = includeFormal
        self.generateVHDL = generateVHDL

        #self.active = F'sbt "runMain {id}"'

    ## ?
    def write(self, code: list[str], overwrite: bool = False):
        buildLines = []
        buildLines.append(F'')
        buildLines.append(F'//Generate the Top Verilog')
        buildLines.append(F'object {self.toplevel}' + ' {')
        buildLines.append('    def main(args: Array[String]) {')
        buildLines.append(F'        SpinalConfig(')
        if not self.verilogPath == None:
            buildLines.append(F'            targetDirectory = "{self.verilogPath}"')
        if self.includeFormal:
            buildLines.append(F'        ).includeFormal.generateSystemVerilog(new {self.toplevel}())')
        else:
            buildLines.append(F'        ).generateSystemVerilog(new {self.toplevel}())')
        buildLines.append('    }')
        buildLines.append('}')

        code = "\n".join(code + buildLines)

        ## check if file exists
        file = self.path + self.id
        if not overwrite and Path(file).exists():
            print("    -> File already exists. Not overwriting.")
        else:
            with open(file, "w") as f:
                f.write(code)
        return self
    
## ?
class BuildSBTFile(File):
    def __init__(self, parent: Folder, spinalVersion: str = '1.8.1', scalaVersion: str = '2.11.12'):
        super().__init__('build.sbt', parent)
        self.type = 'BuildSBTFile'

        code = []
        code.append(F'val spinalVersion = "{spinalVersion}"')
        code.append('')
        code.append('lazy val root = (project in file(".")).')
        code.append('  settings(')
        code.append('    inThisBuild(List(')
        code.append('      organization := "com.github.spinalhdl",')
        code.append(F'      scalaVersion := "{scalaVersion}",')
        code.append('      version      := "2.0.0"')
        code.append('    )),')
        code.append('    libraryDependencies ++= Seq(')
        code.append('      "com.github.spinalhdl" % "spinalhdl-core_2.11" % spinalVersion,')
        code.append('      "com.github.spinalhdl" % "spinalhdl-lib_2.11" % spinalVersion,')
        code.append('      compilerPlugin("com.github.spinalhdl" % "spinalhdl-idsl-plugin_2.11" % spinalVersion),')
        code.append('      "org.scalatest" %% "scalatest" % "3.2.5",')
        code.append('      "org.yaml" % "snakeyaml" % "1.8"')
        code.append('    ),')
        code.append('    name := "VexRiscv"')
        code.append('  )')
        code.append('')
        code.append('  fork := true')

        self.write(code, True)

## ?
class CheckSBYFile(File):
    def __init__(self, toplevel: str, parent: Folder, depth: int, synchronous: bool = True):
        super().__init__('check.sby', parent)
        self.type = 'CheckSBYFile'
        #self.active = F'sby -f Check.sby cover' + '\n' + F'sby -f Check.sby bmc'

        code = []
        code.append(F'[tasks]')
        code.append(F'cover')
        code.append(F'bmc')
        code.append(F'')
        code.append(F'[options]')
        code.append(F'cover: mode cover')
        code.append(F'cover: depth {depth}')
        code.append(F'bmc: mode bmc')
        code.append(F'bmc: depth {depth}')
        code.append(F'')
        code.append(F'[engines]')
        code.append(F'smtbmc yices')
        code.append(F'')
        code.append(F'[script]')
        code.append(F'read_verilog -formal {toplevel}.sv')
        code.append(F'prep -top {toplevel}')
        if synchronous:
            code.append(F'clk2fflogic')
        code.append(F'')
        code.append(F'[files]')
        code.append(F'{toplevel}.sv')
        
        self.write(code, True)

## ?
class ShellScript(File):
    def __init__(self, id: str, parent: Folder):
        super().__init__(id, parent)
        self.type = 'ShellScript'
        self.active = F'chmod +x {id} \n ./{id}'

## ?
class SymbiYosysProof(Folder):
    def __init__(self, id: str, path: str, depth: int, generateShellScript: bool = True):
        super().__init__(id, path)
        self.type = 'SymbiYosysProof'
        self.depth = depth
        self.status = 0

## ?
class FormalHandshakeHardwareProject(Folder):
    def __init__(self, id: str, path: str):
        super().__init__(id,path)
        self.type = 'FormalHandshakeHardwareProject'

    ## ?
    def initialize(self):
        self.openFolder('sources').protect()
        self.openFolder('designs')
        self.openFolder('proofs')
        self.save()
        return self

    @classmethod
    def load(cls, id: str, path: str, update: bool = True, report: bool = True) -> Self:
        instance = super().load(id, path, update, report)
        instance.initialize()
        return instance

    from formalHandshake_Hardware import formalHandshake_Hardware
    
    ## ?
    def addSymbiYosysProof(self, proof: formalHandshake_Hardware.Hardware_Module, designName: str, depth: int, minDepth: int = None, priority: bool = False, overwrite: bool = False, generateBuildFiles: bool = False, report: bool = False):
        proofFolder = self.openFolder('proofs', True).openFolder(designName, True)
        id = proof.className    #proof.id

        if proofFolder.hasFolder(id) and not overwrite:
            if report: print(F'    -> Cannot add SymbiYosys proof "{id}", it allready exists.')
        else:
            if proofFolder.hasFolder(id):
                ## unprotect files:
                proofFolder.getFolder(id).unprotect(True)
                proofFolder.removeFolder(proofFolder.getFolder(id))
            ## create symbiyosys folder
            folder = proofFolder.openFolder(id)
            folder.type = 'SymbiYosysProof'
            if priority:
                folder.tag = 0
            else: 
                folder.tag = 10
        
            folder.value = depth
            if not minDepth == None:
                if not minDepth < depth:
                    raise
                else:
                    folder.value2 = minDepth
            else:
                folder.value2 = depth
            
            folder.files.append(SpinalHDLFile(id, folder, True).write(proof.toSpinalHDL(report = report), True))
            if generateBuildFiles:
                folder.files.append(BuildSBTFile(folder))
                folder.files.append(CheckSBYFile(id, folder, depth))
            
            folder.save()
            return folder

    ## ?
    def addDesign(self, design: formalHandshake_Hardware.Hardware_Module, subFolder: str = None, generateVerilog: bool = False, verilogPath: str = None, overwrite: bool = False, report: bool = False, warnings: bool = False, spinalVersion: str = '1.8.1', scalaVersion: str = '2.11.12'):
        folder = self.openFolder('designs', True)
        if not subFolder == None:
            folder = folder.openFolder(subFolder, True)
        
        id = design.className + '.scala'

        if folder.hasFile(id):
            if not overwrite:
                if warnings:
                    print(F'ProjectManager: cannot write file {folder.path + folder.id + '/' + id}, it already exists')
            else:
                folder.removeFile(folder.getFile(id))

        file = SpinalHDLFile(design.className, folder, False, verilogPath).write(design.toSpinalHDL(report = report), True)
        folder.files.append(file)
        folder.save()

        if generateVerilog:
            path = folder.path + folder.id + '/'
            if Path(path + 'failed_sv_log.txt').exists():
                folder.openFile('failed_sv_log.txt', False).trash()
                folder.clean()
            if report: print(F'        -> trying to build {path + folder.id + '.sv'} file')
            log = None
            sbt = BuildSBTFile(folder, spinalVersion, scalaVersion)
            folder.files.append(sbt)
            sbt.trash()
            folder.openFolder('project').unprotect(True).trash(True)
            folder.openFolder('target').unprotect(True).trash(True)
            folder.save()

            if report: print(F'        -> executing: "sbt runMain {folder.id[0].upper() + folder.id[1:]}" at {path}')
            log = (subprocess.run(['sbt', F'runMain {folder.id[0].upper() + folder.id[1:]}'], cwd = path, capture_output = True, text = True)).stdout
            folder.openFile(folder.id + '.sv')
            folder.clean()

            ## Check if sv file exists
            if not Path(path + folder.id[0].upper() + folder.id[1:] + '.sv').exists():
                code = []
                code.append(log)
                folder.openFile('failed_sv_log.txt', True).write(code, True)
                folder.save()
                if report: print(F'        -> creating {path + folder.id[0].upper() + folder.id[1:] + '.sv'} file failed, see "failed_sv_log.txt"')
            else:
                if report: print(F'        -> created {path + folder.id[0].upper() + folder.id[1:]+ '.sv'} file')
              
        return file

    ## ?
    def yosysProofAutomation(self, update: bool = True, report: bool = False, keepCoverTraces: bool = False, stopOnFail: bool = False, protectFinished: bool = False, synchronous: bool = False, spinalVersion: str = '1.8.1', scalaVersion: str = '2.11.12'):
        print(F'ProjectManager: Running Proof automation for project "{self.id}"')
        ## ?
        def createSVFromSpinalHDL(path: str, toplevel: str, report: bool = False):
            if report:
                subprocess.run(
                    ['sbt', F'runMain {toplevel}'], cwd = path)
            else:
                return subprocess.run(['sbt', F'runMain {toplevel}'], cwd = path, capture_output = True, text = True)
                
        ## ? 
        def runYosysProof(path: str, mode: str = '', report: bool = False):
            if report:
                subprocess.run(['sby', '-f', 'check.sby', mode], cwd = path)
            else:
                return subprocess.run(['sby', '-f', 'check.sby', mode], cwd = path, capture_output = True, text = True)

        if self.hasFolder('proofs') and len(self.getFolder('proofs').subFolders) > 0:
            proofsFolder = self.getFolder('proofs')
            priorityProofs: list[Folder] = []
            proofs: list[Folder] = []
            for folder in proofsFolder.subFolders:
                for subfolder in folder.subFolders:
                    if subfolder.type == 'SymbiYosysProof':
                        if subfolder.tag < 10:
                            priorityProofs.append(subfolder)
                        else:
                            proofs.append(subfolder)
            numPass = 0
            numExecuted = 0
            for p, proof in enumerate(priorityProofs + proofs):
                start = time.perf_counter()
                if report: 
                    print(F'    -> proof {p + 1}/{len(priorityProofs + proofs)} ({numPass}/{numExecuted} passed/executed): {proof.id}')
                else:
                    #sys.stdout.write("\r" + " " * 40 + "\r")
                    sys.stdout.write(f"\r\033[K    -> proof {p + 1}/{len(priorityProofs + proofs)} ({numPass}/{numExecuted} passed/executed): {proof.id}")
                    sys.stdout.flush()
                if proof.protected:
                    if report: print(F'        -> proof is protected (frozen)')
                    if proof.tag == 3 or proof.tag == 13:
                        numPass += 1
                        numExecuted += 1
                        if report: print(F'        -> proof passed')
                    if proof.tag == 4 or proof.tag == 14:
                        numExecuted += 1
                        if report: print(F'        -> proof failed')
                else:
                    proof.unprotect(True)
                    ## ?
                    if update:
                        proof.tag = 0
                    
                    path = proof.path + proof.id + '/'
                        
                    ## 0-9 priority, 10-19 non priority
                    ## 0/10 = initialized
                    ## 1/11 = sv-file generated
                    ## 2/12 = cover depth search done or fixed value chosen and cover executed
                    ## 3/13 = bmc done and passed
                    ## 4/14 = bmc done and failed
                    ## 5/15 = proof protected (frozen)
                    ## 7/17 = problems with file generation
                    ## 8/18 = problems with cover statement -> e.g. ran out of bounds
                    ## 9/19 = problems with proof, could not generate conclusive pass or fail result

                    log = None
                    ## ?
                    if proof.tag == 0 or proof.tag == 10:
                        sbt = BuildSBTFile(proof, spinalVersion, scalaVersion)
                        proof.files.append(sbt)
                        sbt.trash()
                        proof.openFolder('project').unprotect(True).trash(True)
                        proof.openFolder('target').unprotect(True).trash(True)
                        proof.save()
                        log = createSVFromSpinalHDL(path, proof.id).stdout
                        proof.openFile(proof.id + '.sv')
                        if report: print(F'        -> created .sv file')
                        proof.tag += 1
                        proof.clean()

                    ## ?
                    if proof.tag == 1 or proof.tag == 11:
                        ## Check if sv file exists
                        if not Path(path + proof.id + '.sv').exists():
                            code = []
                            code.append(log)
                            proof.openFile('failed_sv_log.txt', True).write(code, True)
                            proof.tag += 6
                            proof.save()
                        else:
                            while proof.value2 <= proof.value and not Path(path + 'check_cover/PASS').exists():
                                if report: 
                                    #print(F'    -> checking cover depth {proof.value2} (limit: {proof.value})')
                                    #sys.stdout.write("\r" + " " * 40 + "\r")
                                    sys.stdout.write(f"\r\033[K        -> checking cover depth {proof.value2} (limit: {proof.value})")
                                    sys.stdout.flush()
                                if proof.hasFile('check.sby'): proof.removeFile(proof.getFile('check.sby'))
                                sby = CheckSBYFile(proof.id, proof, proof.value2, synchronous)
                                sby.trash()
                                proof.files.append(sby)
                                proof.openFolder('check').trash()
                                cover = proof.openFolder('check_cover')
                                proof.save()
                                log = runYosysProof(path, 'cover').stdout
                                if not Path(path + 'check_cover/PASS').exists():
                                    proof.value2 += 1
                                    if not keepCoverTraces:
                                        cover.trash()
                                    proof.clean()
                                else:
                                    if keepCoverTraces:
                                        engine_0 = cover.openFolder('engine_0')
                                        for subPath in Path(cover.path + cover.id).rglob("*"):
                                            if subPath.is_dir() and not subPath.name == 'engine_0':
                                                #print(F'Removing {subPath}')
                                                shutil.rmtree(subPath, ignore_errors=True)
                                            if subPath.is_file():
                                                if (subPath.suffix.lower() == '.vcd'):
                                                    engine_0.openFile(subPath.name)
                                                else:
                                                    subPath.unlink()
                                    else:
                                        cover.trash()
                                    proof.clean()
                                    break
                            
                            if proof.value2 > proof.value:
                                code = []
                                code.append(log)
                                proof.openFile('failed_cover_log.txt', True).write(code, True)
                                if report: 
                                    #print(F'    -> could not reach cover statements with given limit {proof.value}')
                                    sys.stdout.write(f"\r\033[K        -> could not reach cover statements with given limit {proof.value}")
                                    sys.stdout.flush()
                                    print()
                                proof.tag += 7
                            else:
                                if report: 
                                    #print(F'    -> reached all cover statements at depth {proof.value2} (limit: {proof.value})')
                                    sys.stdout.write(f"\r\033[K        -> reached all cover statements at depth {proof.value2} (limit: {proof.value})")
                                    sys.stdout.flush()
                                    print()
                                proof.tag += 1
                            proof.save()
                        endCover = time.perf_counter()
                        proof.value3 = (endCover - start)
                        start = time.perf_counter()

                    ## ?
                    if proof.tag == 2 or proof.tag == 12:
                        ## Check if sv file exists
                        if not Path(path + proof.id + '.sv').exists():
                            proof.tag += 6
                            proof.save()
                        else:
                            if report: 
                                print(F'        -> executing bmc with depth {proof.value2}')
                            #print(F' -> Executing bmc with depth {proof.value2}')
                            if proof.hasFile('check.sby'):
                                proof.removeFile(proof.getFile('check.sby'))
                            sby = CheckSBYFile(proof.id, proof, proof.value2, synchronous)
                            sby.trash()
                            proof.files.append(sby)
                            proof.openFolder('check').trash()
                            bmc = proof.openFolder('check_bmc').trash()
                            proof.save()
                            log = runYosysProof(path, 'bmc').stdout
                            if not (Path(path + 'check_bmc/PASS').exists() or Path(path + 'check_bmc/FAIL').exists()):
                                ## storing log file
                                code = []
                                code.append(log)
                                proof.openFile('inconclusive_log.txt', True).write(code, True)
                                proof.tag += 7
                            else:
                                if not Path(path + 'check_bmc/PASS').exists():
                                    ## storing log file
                                    code = []
                                    code.append(log)
                                    proof.openFile('failed_bmc_log.txt', True).write(code, True)
                                    bmc.keep()
                                    engine_0 = bmc.openFolder('engine_0')
                                    for subPath in Path(bmc.path + bmc.id).rglob("*"):
                                        if subPath.is_dir() and not subPath.name == 'engine_0':
                                            #print(F'Removing {subPath}')
                                            shutil.rmtree(subPath, ignore_errors=True)
                                        if subPath.is_file():
                                            if (subPath.suffix.lower() == '.vcd'):
                                                engine_0.openFile(subPath.name)
                                            else:
                                                subPath.unlink()
                                    proof.tag += 2
                                else:
                                    proof.tag += 1
                            proof.clean()

                    ## ?
                    if proof.tag == 3 or proof.tag == 13:
                        numPass += 1
                        numExecuted += 1
                        if report: print(F'        -> proof passed')
                        if protectFinished:
                            proof.protect()

                    ## ?
                    if proof.tag == 4 or proof.tag == 14:
                        numExecuted += 1
                        if report: print(F'        -> proof failed')
                        if stopOnFail:
                            if report:
                                print(F'    -> proof {proof.id} failed, stopping ({numPass}/{numExecuted} passed)')
                            else:
                                sys.stdout.write(f"\r\033    -> proof {proof.id} failed, stopping ({numPass}/{numExecuted} passed)")
                                sys.stdout.flush()
                                print()
                            return self

                    ## ?
                    if proof.tag == 7 or proof.tag == 17:
                        if report: print(F'        -> proof is missing .sv file, cannot proceed')
                    
                    ## ?
                    if proof.tag == 8 or proof.tag == 18:
                        if report: print(F'        -> proof could not reach cover statements -> store log file?')
                    
                    ## ?
                    if proof.tag == 9 or proof.tag == 19:
                        if report: print(F'        -> proof could not produce conclusive result')
                
                end = time.perf_counter()
                proof.value4 = (end - start)
                if report: 
                    print(F'    -> proof {p + 1}/{len(priorityProofs + proofs)} finished ({numPass}/{numExecuted} passed/executed): {proof.id}, time cover: {proof.value3:.6f}s, time bmc {proof.value4:.6f}s')

            if report:
                print(F'    -> done, {numPass}/{numExecuted} passed')
            else:
                #sys.stdout.write("\r" + " " * 40 + "\r")
                sys.stdout.write(f"\r\033[K    -> done, {numPass}/{numExecuted} passed")
                sys.stdout.flush()
                print()
        else:
            print(F'    -> currently has no proofs to be executed')
        
        return self
    
    ## ?
    def getStatus(self, detailed: bool = False, createResultFile: bool = False):
        line = F'ProjectManager: Yosys proof status for project "{self.id}"'
        code: list = []
        print(line)
        if self.hasFolder('proofs'):
            proofsFolder = self.getFolder('proofs')
            if proofsFolder.hasFile('results.txt'):
                proofsFolder.removeFile(proofsFolder.getFile('results.txt'))
            if len(proofsFolder.subFolders) > 0:
                if createResultFile:
                    code.append(line)
                for folder in proofsFolder.subFolders:
                    design = folder.id
                    proofs: int = 0
                    executed: int = 0
                    passed: int = 0
                    executionFailed: int = 0
                    for proof in folder.subFolders:
                        proofs += 1
                        if proof.tag == 3 or proof.tag == 13:
                            executed += 1
                            passed += 1
                        if proof.tag == 4 or proof.tag == 14:
                            executed += 1
                        if proof.tag == 7 or proof.tag == 17 or proof.tag == 8 or proof.tag == 18  or proof.tag == 9 or proof.tag == 19:
                            executionFailed += 1
                    line = F'    {design}:'
                    print(line)
                    if createResultFile:
                        code.append(line)
                    if proofs > 0:
                        line = F'    - executed: {executed}/{proofs}'
                        print(line)
                        if createResultFile:
                            code.append(line)
                    if executed > 0:
                        line = F'    - passed:   {passed}/{executed}'
                        print(line)
                        if createResultFile:
                            code.append(line)
                    if executionFailed > 0:
                        line = F'    - problems: {executionFailed}/{proofs}'
                        print(line)
                        if createResultFile:
                            code.append(line)

                    if detailed or createResultFile:
                        for proof in folder.subFolders:
                            status = 'initialized'
                            if proof.tag == 1 or proof.tag == 11:
                                status = 'sv-file generated'
                            if proof.tag == 2 or proof.tag == 12:
                                status = F'cover done, depth: {proof.value2}'
                            if proof.tag == 3 or proof.tag == 13:
                                status = 'bmc done and passed'
                            if proof.tag == 4 or proof.tag == 14:
                                status = 'bmc done and failed'
                            if proof.tag == 7 or proof.tag == 17:
                                status = 'problems with file generation'
                            if proof.tag == 8 or proof.tag == 18:
                                status = 'problems with cover statement'
                            if proof.tag == 9 or proof.tag == 19:
                                status = 'problems with proof, could not generate conclusive pass or fail result'
                            status += F' (time cover: {proof.value3:.6f}s, time bmc {proof.value4:.6f}s)'
                            depth = F'{proof.value}'
                            if proof.value2 < proof.value:
                                depth = F'{proof.value2} (max {proof.value})'
                            line = F'        -> proof: {proof.id}, depth: {depth}, status: {status}'
                            if detailed:
                                print(line)
                            if createResultFile:
                                code.append(line)
                if createResultFile:
                    proofsFolder.openFile('results.txt', True).write(code, True)
            else: print(F'    -> proof folder is empty')

        else: print(F'    -> no proof folder')
        
