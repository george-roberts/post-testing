#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback, os, tempfile

app = adsk.core.Application.get()
if app:
    ui = app.userInterface
projectFolder = None
outputFolder = None
handlers = []
differences = []

def run(context):
    try:
        ## Set the project ID for the NC testing project
        testingProjectID = 'a.YnVzaW5lc3M6YXV0b2Rlc2szNTQ2IzIwMjMwMzEwNjE5MTgxMDc2'
        global projectFolder, outputFolder
        ## Get the testing project
        testingProject = app.data.dataProjects.itemById(testingProjectID)
        ## Get the folder that stores the Fusion files
        projectFolder = testingProject.rootFolder.dataFolders.itemByName('Projects')
        ## Get the folder that stores the NC code
        outputFolder = testingProject.rootFolder.dataFolders.itemByName('Outputs')
        
        ## Create a progress dialog
        progressDialog = ui.createProgressDialog()
        progressDialog.isCancelButtonShown = True
        progressDialog.cancelButtonText = 'Stop'
        progressDialog.show('Testing progress', 'Post processor testing progress', 0, projectFolder.dataFiles.count, 0)
        ## Iterate through every file in the project folder (if the progress dialog was 'cancelled' it will not proceed with another file)
        for file in projectFolder.dataFiles:
            if progressDialog.wasCancelled:
                return
            ## open the file
            document = app.documents.open(file, True)
            ## post each NC program and compare
            postAndCompare(document)
            progressDialog.progressValue += 1

        if len(differences) > 0:
            ui.messageBox('There were ' + str(len(differences)) + ' differences in: \n' + '\n'.join(differences))

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def postAndCompare(document: adsk.core.Document):
    global projectFolder, outputFolder
    ## Get the CAM product (so we can access the NC program)
    cam = adsk.cam.CAM.cast(document.products.itemByProductType('CAMProductType'))
    ## get a list of all nc programs
    ncPrograms = cam.ncPrograms
    ## get the output folder (based on doc name)
    projectNCFolder = outputFolder.dataFolders.itemByName(document.name)
    firstRun = False
    ## if the output folder doesn't exist, this document hasn't been run before
    if not projectNCFolder:
        firstRun = True
        ## create the output folder
        projectNCFolder = outputFolder.dataFolders.add(document.name)
        ui.messageBox('Output files for this version of the file have not been found. Uploading new output files to Fusion team')
    ## go through every NC program in the document
    for ncProgram in ncPrograms:
        ## ensure the editor doesn't keep opening when posting
        ncProgram.parameters.itemByName('nc_program_openInEditor').expression = "false"
        ## make a temporary directory to post to
        tmpDir = tempfile.mkdtemp()
        ## set the output folder
        ncProgram.parameters.itemByName('nc_program_output_folder').expression = "'" + tmpDir.replace('\\', '/') + "'"
        ## Post the NC program
        ncProgram.postProcess()
        ## get a list of all files in the output director (this should ensure that subprograms are checked)
        filenames = next(os.walk(tmpDir), (None, None, []))[2]
        ## go through every file
        for filename in filenames:
            ## construct the full filepath
            fullPath = os.path.join(tmpDir, filename)
            ## upload the file as a txt file if it's the first ever run
            if firstRun:
                os.rename(fullPath, fullPath + '.txt')
                fullPath = fullPath + '.txt'
                projectNCFolder.uploadFile(fullPath)
            ## if it has been run before, download the file and compare it
            else:
                for file in projectNCFolder.dataFiles:
                    if filename in file.name:
                        ## set the name to download as
                        tmpName = os.path.join(tmpDir, filename + '_old')
                        ## download the file
                        file.download(tmpName, None)
                        ## if the file downloaded correctly, diff it
                        if os.path.exists(tmpName):
                            diffFiles(tmpName, fullPath, document.name, ncProgram.name)
    return 

## simply open up each file and store the contents as a string. Then, compare the two strings
## This WILL NOT work if there is a date or something in the NC output. But, basic string manipulation could solve that
## the return value will determine if we continue or not
def diffFiles(fileOne, fileTwo, projectName, ncProgramName):
    newNCCode = ''
    oldNCCode = ''
    global differences
    ## read the contents
    with open(fileOne, 'r') as file:
        newNCCode = file.read()
    with open(fileTwo, 'r') as file:
        oldNCCode = file.read()
    if newNCCode != oldNCCode:
        differences.append('File: ' + projectName + ' NCProgram: ' + ncProgramName)
        ## ask the user if they would like to see the files
        result = ui.messageBox('NC Code for this project is different! \n Would you like to open in the files?', 'Difference in output', adsk.core.MessageBoxButtonTypes.YesNoButtonType)
        if result == adsk.core.DialogResults.DialogYes:
            ## open both files with the system default app
            os.system(fileOne)
            os.system(fileTwo)
        ## if there has been an error, ask the user if they want to continue. Maybe I should ask if they want to upload the new version (if the change is OK)
        cont = ui.messageBox('Would you like to continue the test?', 'Continue?', adsk.core.MessageBoxButtonTypes.YesNoButtonType)
        if cont == adsk.core.DialogResults.DialogYes:
            return True
        else:
            return False
    else:
        return True
