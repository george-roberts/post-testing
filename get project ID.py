#Author-
#Description-

import adsk.core, adsk.fusion, adsk.cam, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        ui.messageBox(app.data.activeProject.id)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
