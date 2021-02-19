
import configparser
import sys
from subprocess import call
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import pyqtRemoveInputHook
from PyQt5.QtWidgets import QPushButton, QCheckBox, QWidget, QVBoxLayout, QLabel, QGroupBox, \
    QHBoxLayout, QLineEdit, QRadioButton, QGridLayout, QComboBox, QFileDialog, QApplication, \
    QTabWidget, QInputDialog, QScrollArea, QMessageBox, QGraphicsDropShadowEffect
from PyQt5.QtGui import QCursor

import Options
import Randomizer
import Update
import Constants
import time
import traceback


if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required. Report this to Green Knight")

# Extended QButton widget to hold flag value - NOT USED PRESENTLY
class FlagButton(QPushButton):
    def __init__(self, text, value):
        super(FlagButton, self).__init__()
        self.setText(text)
        self.value = value

# Extended QCheckBox widget to hold flag value - CURRENTLY USED
class FlagCheckBox(QCheckBox):
    def __init__(self, text, value):
        super(FlagCheckBox, self).__init__()
        self.setText(text)
        self.value = value


class Window(QWidget):

    def __init__(self):
        super().__init__()

        # window geometry data
        self.title = "Beyond Chaos Randomizer"
        self.left = 200
        self.top = 200
        self.width = 700
        self.height = 600

        # values to be sent to Randomizer
        self.romText = ""
        self.version = "4"
        self.mode = "normal" # default
        self.seed = ""
        self.flags = []


        # dictionaries to hold flag data
        self.aesthetic = {}
        self.sprite = {}
        self.experimental = {}
        self.gamebreaking = {}
        self.major = {}
        self.flag = {}
        self.battle = {}
        self.beta = {}
        self.dictionaries = [self.flag, self.sprite, self.aesthetic, self.major,
                              self.experimental, self.gamebreaking, self.battle, self.beta]
        #keep a list of all checkboxes
        self.checkBoxes = []

        # dictionary? of saved presets
        self.savedPresets = {}

        # array of supported game modes
        self.supportedGameModes = ["normal", "katn", "ancientcave", "speedcave", "racecave", "dragonhunt" ]
        # dictionary of game modes for drop down
        self.GameModes = {}

        # array of preset flags and codes
        self.supportedPresets = ["newplayer", "intermediateplayer", "advancedplayer", "raceeasy", "racemedium", "raceinsane" ]
        # dictionay of game presets from drop down
        self.GamePresets = {}

        # ui elements
        self.flagString = QLineEdit() #flag text box for displaying the flags
        self.comboBox = QComboBox() #flag saved preset dropdown
        self.modeBox = QComboBox() #game mode drop down to pick what gamemode
        self.presetBox = QComboBox() #official supported preset flags
        self.modeDescription = QLabel("Pick a Game Mode!")
        #tabs: Flags, Sprites, Battle, etc...
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()
        self.tab7 = QWidget()
        self.tab8 = QWidget()

        self.middleLeftGroupBox = QGroupBox() #obsolted
        self.tablist = [self.tab1, self.tab2, self.tab3, self.tab4, self.tab5, self.tab6, self.tab7, self.tab8]

        #global busy notifications
        flagsChanging = False

        # ----------- Begin buiding program/window ------------------------------

        # pull data from files
        self.initCodes()
        self.compileSavedPresets()
        

        # create window using geometry data
        self.InitWindow()

        self.romInput.setText(self.romText)
        self.updateDictionaries()
        self.updateFlagString()
        self.updateFlagCheckboxes()
        self.flagButtonClicked()

    def InitWindow(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        
        # build the UI
        self.CreateLayout()

        # show program onscreen
        self.showMaximized()    #maximize the randomizer
        self.clearUI()          #clear the UI of all selections

    def CreateLayout(self):
        # Primary Vertical Box Layout
        vbox = QVBoxLayout()

        titleLabel = QLabel("Beyond Chaos Randomizer")
        font = QtGui.QFont("Arial", 24, QtGui.QFont.Black)
        titleLabel.setFont(font)
        titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        titleLabel.setMargin(25)
        vbox.addWidget(titleLabel)
        

        vbox.addWidget(self.GroupBoxOneLayout()) 
        vbox.addWidget(self.GroupBoxTwoLayout()) # Adding second groupbox to the layout
        vbox.addWidget(self.GroupBoxThreeLayout()) # Adding second/middle groupbox
        vbox.addWidget(self.GroupBoxFourLayout()) # Adding third/bottom groupbox

        self.setLayout(vbox)

    def update(self):
        QMessageBox.information(self, "Update Process", "Checking for updates, if found this will automatically close", QMessageBox.Ok)
        Update.update()

    # Top groupbox consisting of ROM selection, and Seed number input
    def GroupBoxOneLayout(self):
        topGroupBox = QGroupBox()
        TopHBox = QHBoxLayout()

        romLabel = QLabel("ROM:")
        TopHBox.addWidget(romLabel)
        self.romInput = QLineEdit()
        self.romInput.setPlaceholderText("Required - Will save to presets")
        self.romInput.setReadOnly(True)
        TopHBox.addWidget(self.romInput)

        browseButton = QPushButton("Browse")
        browseButton.clicked.connect(lambda: self.openFileChooser())
        TopHBox.addWidget(browseButton)
        seedLabel = QLabel("Seed:")
        TopHBox.addWidget(seedLabel)
        self.seedInput = QLineEdit()
        self.seedInput.setPlaceholderText("Optional - WILL NOT SAVE TO PRESETS!")
        TopHBox.addWidget(self.seedInput)

        #radioButton.clicked.connect(lambda: self.updateRadioSelection("racecave"))
        topGroupBox.setLayout(TopHBox)

        return topGroupBox

    def GroupBoxTwoLayout(self):
        self.compileModes()
        self.compileSupportedPresets()
        groupBoxTwo = QGroupBox()
        middleHBox = QHBoxLayout()
        middleHBox.addStretch(0)

        # ---- Game Mode Drop Down ---- #
        gameModeLabel = QLabel("Game Modes: a")
        gameModeLabel.setMaximumWidth(60)
        middleHBox.addWidget(gameModeLabel, alignment = QtCore.Qt.AlignLeft)
       
        self.modeBox.addItem("Select a mode")
        for item in self.GameModes.items():
            self.modeBox.addItem(item[0])
        self.modeBox.currentTextChanged.connect(lambda: self.updateGameDescription())
        middleHBox.addWidget(self.modeBox, alignment = QtCore.Qt.AlignLeft)

        # ---- Mode Description ---- #
        self.modeDescription.setStyleSheet("font-size:18px; height:24px; color:#253340;")
        middleHBox.addWidget(self.modeDescription, alignment = QtCore.Qt.AlignLeft)
        
        # ---- Preset Flags Drop Down ---- #
        presetModeLabel = QLabel("Preset Modes: a")
        presetModeLabel.setMaximumWidth(60)
        middleHBox.addWidget(presetModeLabel, alignment = QtCore.Qt.AlignLeft)
        self.presetBox.addItem("Select a mode")
        for item in self.GamePresets.items():
            self.presetBox.addItem("")    
            
        self.presetBox.currentTextChanged.connect(lambda: self.updatePresetDropdown())
        middleHBox.addWidget(self.presetBox,alignment = QtCore.Qt.AlignLeft)
        
        # ---- Update Button ---- #
        updateButton = QPushButton("Check for Updates")
        updateButton.setStyleSheet("font:bold; font-size:18px; height:24px; background-color: #5A8DBE; color: #E4E4E4;")
        width = 250
        height = 60
        updateButton.setMaximumWidth(width)
        updateButton.setMaximumHeight(height)
        updateButton.clicked.connect(lambda: self.update())
        updateButton.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(3);
        updateButton.setGraphicsEffect(effect);
        middleHBox.addWidget(updateButton,alignment = QtCore.Qt.AlignLeft )
        
        groupBoxTwo.setLayout(middleHBox)
        return groupBoxTwo



    # Middle groupbox of sub-groupboxes. Consists of left section (game mode selection)
    #   and right section (flag selection -> tab-sorted)
    def GroupBoxThreeLayout(self):
        groupBoxTwo = QGroupBox()
        middleHBox = QHBoxLayout()
        
        #obsoleted
        # ------------ Part one (left side) of middle section - Mode radio buttons -------

        #self.middleLeftGroupBox.setTitle("Select Mode")
        #midLeftVBox = QVBoxLayout()

        #radioButton = QRadioButton("Normal (Default)")
        #radioButton.setToolTip("Play through the normal story")
        #radioButton.setChecked(True)
        #radioButton.mode = "normal"
        #radioButton.clicked.connect(lambda: self.updateRadioSelection("normal"))
        #midLeftVBox.addWidget(radioButton)

        #radioButton = QRadioButton("Ancient Cave")
        #radioButton.setToolTip("Play though a long randomized dungeon")
        #radioButton.mode = "ancientcave"
        #radioButton.clicked.connect(lambda: self.updateRadioSelection("ancientcave"))
        #midLeftVBox.addWidget(radioButton)

        #radioButton = QRadioButton("Speed Cave")
        #radioButton.setToolTip("Play through a medium-sized randomized dungeon")
        #radioButton.mode = "speedcave"
        #radioButton.clicked.connect(lambda: self.updateRadioSelection("speedcave"))
        #midLeftVBox.addWidget(radioButton)

        #radioButton = QRadioButton("Race Cave")
        #radioButton.setToolTip("Play through a short randomized dungeon")
        #radioButton.mode = "racecave"
        #radioButton.clicked.connect(lambda: self.updateRadioSelection("racecave"))
        #midLeftVBox.addWidget(radioButton)

        #radioButton = QRadioButton("Kefka@Narshe")
        #radioButton.setToolTip("Play the normal story up to Kefka at Narshe, "
        #                       "with extra wackiness. Intended for racing.")
        #radioButton.mode = "katn"
        #radioButton.clicked.connect(lambda: self.updateRadioSelection("katn"))
        #midLeftVBox.addWidget(radioButton)

        #radioButton = QRadioButton("Dragon Hunt")
        #radioButton.setToolTip("Kill all 8 dragons in the World of Ruin. Intended for racing.")
        #radioButton.mode = "dragonhunt"
        #radioButton.clicked.connect(lambda: self.updateRadioSelection("dragonhunt"))
        #midLeftVBox.addWidget(radioButton)

        #self.middleLeftGroupBox.setLayout(midLeftVBox)
        # ------------- Part one (left side) end ----------------------------------------------

        # ------------- Part two (right side) of middle section - Flag tabs -----------------
        middleRightGroupBox = QGroupBox("Flag Selection")
        tabVBoxLayout = QVBoxLayout()
        tabs = QTabWidget()
        tabNames = ["Flags", "Sprites", "Battle", "Aesthetic", "Major", "Experimental", "Gamebreaking", "Beta"]

        ############## Only checkboxes, no inline description ###############

        # # loop to add tab objects to 'tabs' TabWidget
        #
        # for tabObj, name in zip(self.tablist, tabNames):
        #     tabs.addTab(tabObj, name)
        #
        # for t, d in zip(self.tablist, self.dictionaries):
        #     flagGrid = QGridLayout()
        #     count = 0
        #     for flagname, flagdesc in d.items():
        #         cbox = FlagCheckBox(flagname, flagname)
        #         cbox.setCheckable(True)
        #         if flagdesc['checked']:
        #             cbox.isChecked = True
        #         cbox.setToolTip(flagdesc['explanation'])
        #         cbox.clicked.connect(lambda checked : self.flagButtonClicked())
        #         flagGrid.addWidget(cbox, count / 3, count % 3)
        #         count += 1
        #     t.setLayout(flagGrid)


        ############## Checkboxes and inline descriptions #####################

        # loop to add tab objects to 'tabs' TabWidget
        for t, d, names in zip(self.tablist, self.dictionaries, tabNames):
            tabObj = QScrollArea()
            tabs.addTab(tabObj, names)
            tablayout = QVBoxLayout()
            for flagname, flagdesc in d.items():
                cbox = FlagCheckBox(f"{flagname}  -  {flagdesc['explanation']}", flagname)
                self.checkBoxes.append(cbox)
                tablayout.addWidget(cbox)
                #cbox.setCheckable(True)
                #cbox.setToolTip(flagdesc['explanation'])
                cbox.clicked.connect(lambda checked: self.flagButtonClicked())
            t.setLayout(tablayout)
            #tablayout.addStretch(1)
            tabObj.setWidgetResizable(True)
            tabObj.setWidget(t)

        tabVBoxLayout.addWidget(tabs)
        #----------- tabs done ----------------------------

        # this is the line in the layout that displays the string of selected flags
        #   and the button to save those flags
        widgetV = QWidget()
        widgetVBoxLayout = QVBoxLayout()
        widgetV.setLayout(widgetVBoxLayout)

        widgetVBoxLayout.addWidget(QLabel("Text-string of selected flags:"))
        self.flagString.textChanged.connect(self.textchanged)
        widgetVBoxLayout.addWidget(self.flagString)

        saveButton = QPushButton("Save flags selection")
        saveButton.clicked.connect(lambda: self.saveSeed())
        widgetVBoxLayout.addWidget(saveButton)

        # This part makes a group box and adds the selected-flags display
        #   and a button to clear the UI
        flagTextWidget = QGroupBox()
        flagTextHBox = QHBoxLayout()
        flagTextHBox.addWidget(widgetV)
        clearUiButton = QPushButton("Reset")
        clearUiButton.setStyleSheet("font:bold; font-size:16px; height:60px; background-color: #5A8DBE; color: #E4E4E4;")
        clearUiButton.clicked.connect(lambda: self.clearUI())
        clearUiButton.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(3);
        clearUiButton.setGraphicsEffect(effect);
        flagTextHBox.addWidget(clearUiButton)
        flagTextWidget.setLayout(flagTextHBox)

        tabVBoxLayout.addWidget(flagTextWidget)
        middleRightGroupBox.setLayout(tabVBoxLayout)
        # ------------- Part two (right) end ---------------------------------------


        # add widgets to HBoxLayout and assign to middle groupbox layout
        middleHBox.addWidget(middleRightGroupBox)
        groupBoxTwo.setLayout(middleHBox)

        return groupBoxTwo

  
                        

    # Bottom groupbox consisting of saved seeds selection box, and button to generate seed
    def GroupBoxFourLayout(self):
        bottomGroupBox = QGroupBox()
        bottomHBox = QHBoxLayout()

        bottomHBox.addWidget(QLabel("Saved flag selection: "))

        self.comboBox.addItem("Select a preset")
        for string in self.savedPresets:
            self.comboBox.addItem(string)
        self.comboBox.currentTextChanged.connect(lambda: self.updatePresetDropdown())
        bottomHBox.addWidget(self.comboBox)

        #todo: Add amount of seeds to generate here.
        #todo: Add retry on failure checkbox

        deleteButton = QPushButton("Delete selection")
        deleteButton.clicked.connect(lambda: self.deleteSeed())
        bottomHBox.addWidget(deleteButton)

        bottomHBox.addStretch(1)

        generateButton = QPushButton("Generate Seed")
        generateButton.setStyleSheet("font:bold; font-size:18px; height:48px; width:150px")
        generateButton.clicked.connect(lambda: self.generateSeed())
        bottomHBox.addWidget(generateButton)

        bottomGroupBox.setLayout(bottomHBox)
        return bottomGroupBox

    # --------------------------------------------------------------------------------
    # -------------- NO MORE LAYOUT DESIGN PAST THIS POINT ---------------------------
    # --------------------------------------------------------------------------------

    def textchanged(self, text):
        if (self.flagsChanging):
            return
        values = text.split()
        self.flags.clear()
        self.flagString.clear()
        for v in values:
            for d in self.dictionaries:
                for flagname in d:
                    if v == flagname:
                        for c in self.checkBoxes:
                            if v== c.value:
                                c.setChecked(True)
                                self.flags.append(c.value)
                                self.updateFlagString()


    # (At startup) Opens reads code flags/descriptions and
    #   puts data into separate dictionaries
    def initCodes(self):
        for code in Options.NORMAL_CODES + Options.MAKEOVER_MODIFIER_CODES:
            if code.category == "aesthetic":
                d = self.aesthetic
            elif code.category == "sprite":
                d = self.sprite
            elif code.category == "experimental":
                d = self.experimental
            elif code.category == "gamebreaking":
                d = self.gamebreaking
            elif code.category == "major":
                d = self.major
            elif code.category == "beta":
                d = self.beta
            elif code.category == "battle":
                d = self.battle
            else:
                print(f"Code {code.name} does not have a valid category.")
                continue

            d[code.name] = {'explanation': code.long_description, 'checked': False}

        for flag in sorted(Options.ALL_FLAGS):
            self.flag[flag.name] = {'explanation': flag.description, 'checked': True}


    # opens input dialog to get a name to assign a desired seed flagset, then saves flags and selected mode to the cfg file
    def saveSeed(self):
        text, okPressed = QInputDialog.getText(self, "Save Seed", "Enter a name for this flagset", QLineEdit.Normal, "")
        if okPressed and text != '':
            self.savedPresets[text] = f"{self.version}.{self.mode}.{self.flags}."
            config = configparser.ConfigParser()
            config.read('bcex.cfg')
            config['presets'] = self.savedPresets
            with open('bcex.cfg', 'w') as cfg_file:
                config.write(cfg_file)
            self.comboBox.addItem(text) # update drop-down list with new preset
            index = self.comboBox.findText(text)
            self.comboBox.setCurrentIndex(index)


    # delete preset. Dialog box confirms users choice to delete. check is done to ensure file
    #   exists before deletion is attempted.
    def deleteSeed(self):
        seed = self.comboBox.currentText()

        if not seed == "Select a preset":
            response = QMessageBox.question(self, 'Delete confimation', f"Do you want to delete \'{seed}\'?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response == QMessageBox.Yes:
                del self.savedPresets[seed]
                self.comboBox.removeItem(self.comboBox.findText(seed))

    def updateGameDescription(self):
        self.modeDescription.clear()
        index = self.modeBox.currentIndex()
        for item in self.GameModes.items():
            if index == 1:
                if item[0] == "Normal":
                    self.modeDescription.setText(item[1])
            elif index == 2:
                if item[0] == "Kefka @ Narshe":
                    self.modeDescription.setText(item[1])
            elif index == 3:
                if item[0] == "Ancient Cave":
                    self.modeDescription.setText(item[1])
            elif index == 4:
                if item[0] == "Speed Cave":
                    self.modeDescription.setText(item[1])
            elif index == 5:
                if item[0] == "Race Cave":
                    self.modeDescription.setText(item[1])
            elif index == 6:
                if item[0] == "Dragon Hunt":
                    self.modeDescription.setText(item[1])
            else:
                self.modeDescription.setText("Pick a Game Mode!")

        
         
        

    # when preset is selected from dropdown list, load the data into dictionaries
    #   and set the UI to reflect the settings stored in the preset.
    # if the only saved preset is deleted, or user selects initial value of
    #   'Select a preset' then the UI is reset (mainly to avoid runtime errors)
    def updatePresetDropdown(self):
        if self.comboBox.currentIndex() != 0: # text = "Select a preset"
            selectedPreset = self.comboBox.currentText()
            self.loadPreset(selectedPreset)
        else:
            self.clearUI()


        #todo: Fix the UI clearing based on new UI placement.
    # clear/reset UI and clear window object variables. Then reset data dictionaries
    #   to the default state of unset/unchecked flags and mode
    def clearUI(self):
        self.mode = "normal"
        self.seed = ""
        self.flags.clear
        self.seedInput.setText(self.seed)
        self.flagString.clear()
        self.flags.clear()

        for i in self.middleLeftGroupBox.findChildren((QRadioButton)):
            if i.mode == 'normal':
                i.setProperty('checked', True)
                break

        self.comboBox.setCurrentIndex(0)

        self.initCodes()
        self.updateDictionaries()
        self.updateFlagString()
        self.updateFlagCheckboxes()
        self.flagButtonClicked()


    # when flag UI button is checked, update corresponding dictionary values
    def flagButtonClicked(self):
        self.flags.clear()
        for t, d in zip(self.tablist, self.dictionaries):
            children = t.findChildren(FlagCheckBox)
            for c in children:
                if c.isChecked():
                    d[c.value]['checked'] = True
                    flagset = False
                    for flag in self.flags:
                        if flag==d[c.value]:
                            flagset = true
                    if flagset == False:
                        self.flags.append(c.value)
                else:
                    d[c.value]['checked'] = False
        self.updateDictionaries()
        self.updateFlagString()


    # Opens file dialog to select rom file and assigns it to value in parent/Window class
    def openFileChooser(self):
        file_path = QFileDialog.getOpenFileName(self, 'Open File', './',
                                                filter="ROMs (*.smc *.sfc *.fig);;All Files(*.*)")

        # display file location in text input field
        self.romInput.setText(str(file_path[0]))


    def compileSavedPresets(self):
        config = configparser.ConfigParser()
        config.read('bcex.cfg')

        self.romText = config.get('ROM', 'path', fallback='')

        if 'presets' in config:
            self.savedPresets = config['presets']
        if 'speeddial' in config:
            for k, v in config['speeddial'].items():
                if 'speeddial_{k}' not in self.savedPresets:
                    self.savedPresets[f'speeddial_{k}'] = f"4.normal.{v}."
        self.savedPresets['recommended new player preset'] = "4.normal.-dfklu partyparty makeover johnnydmad."

    def compileModes(self):
        for mode in self.supportedGameModes:
            if mode == "normal":
                self.GameModes['Normal'] = "Play through the normal story with randomized gameplay."
            elif mode == "katn":
                self.GameModes['Kefka @ Narshe'] = "Play the normal story up to Kefka at Narshe, with extra wackiness. Intended for racing."
            elif mode == "ancientcave":
                self.GameModes['Ancient Cave'] = "Play though a long randomized dungeon"
            elif mode == "speedcave":
                self.GameModes['Speed Cave'] = "Play through a medium-sized randomized dungeon."
            elif mode == "racecave":
                self.GameModes['Race Cave'] = "Play through a short randomized dungeon"
            elif mode == "dragonhunt":
                self.GameModes['Dragon Hunt'] = "Kill all 8 dragons in the World of Ruin. Intended for racing."

    def compileSupportedPresets(self):
        #self.supportedPresets = ["newplayer", "intermediateplayer", "advancedplayer", "raceeasy", "racemedium", "raceinsane" ]
        for mode in self.supportedGameModes:
            if mode == "newplayer":
                self.GameModes['New Player'] = "d f k l u alasdraco capslockoff partyparty makeover johnnydmad"
            elif mode == "intermediateplayer":
                self.GameModes['Intermediate Player'] = "d f g i k l m o p u w z alasdraco capslockoff makeover partyparty johnnydmad notawaiter mimetime"
            elif mode == "advancedplayer":
                self.GameModes['Advanced Player'] = "b c d e f g i j k l m n o p q r s t u w y z alasdraco capslockoff johnnydmad makeover notawaiter partyparty dancingmaduin bsiab mimetime randombosses"
            elif mode == "raceeasy":
                self.GameModes['Race - Easy'] = "b c d e f g i j k m n o p q r s t w y z capslockoff johnnydmad makeover notawaiter partyparty madworld"
            elif mode == "racemedium":
                self.GameModes['Race - Medium'] = "b c d e f g i j k m n o p q r s t u w y z capslockoff johnnydmad makeover notawaiter partyparty electricboogaloo randombosses madworld"
            elif mode == "raceinsane":
                self.GameModes['Race - Insane'] = "b c d e f g i j k m n o p q r s t u w y z capslockoff johnnydmad makeover notawaiter partyparty darkworld madworld bsiab electricboogaloo randombosses"


    # Reads dictionary data from text file and populates class dictionaries
    def loadPreset(self, flagdict):
        parts = self.savedPresets[flagdict].split('.')
        try:
            unused_version = parts[0]
            mode = parts[1]
            flagstring = parts[2]
        except KeyError:
            QMessageBox.about(self, "Error", "Invalid preset!")
            self.savedPresets.remove(flagdict)
            return

        flags, codes = Options.read_Options_from_string(flagstring, mode)

        for d in self.dictionaries:
            for flagdesc in d.values():
                flagdesc['checked'] = False

        for flag in flags:
            self.flag[flag.name]['checked'] = True

        for code in codes:
            if code.category == "aesthetic":
                d = self.aesthetic
            elif code.category == "sprite":
                d = self.sprite
            elif code.category == "experimental":
                d = self.experimental
            elif code.category == "gamebreaking":
                d = self.gamebreaking
            elif code.category == "major":
                d = self.major
            elif code.category == "battle":
                d = self.battle
            elif code.category == "beta":
                d = self.beta
            else:
                print(f"Code {code.name} does not have a valid category.")
                continue

            d[code.name]['checked'] = True

        self.mode = mode

        # update 'dictionaries' list with updated/populated data dictionaries
        self.updateDictionaries()

        # call functions to update UI based upon preset data loaded from file
        self.updateFlagString()
        self.updateFlagCheckboxes()
        self.updateModeSelection()

    # Get seed generation parameters from UI to prepare for seed generation
    # This will show a confirmation dialog, and call the local Randomizer.py file
    #   and pass arguments to it
    def generateSeed(self):

        self.romText = self.romInput.text()
        if self.romText == "":  # Checks if user ROM is blank
            QMessageBox.about(self, "Error", "You need to select a FFVI rom!")
        else:
            self.seed = self.seedInput.text()

            displaySeed = self.seed
            if self.seed == "":
                displaySeed = "(none)" # pretty-printing :)

            flagMode =""
            for flag in self.flags:
                flagMode += flag

                flagMsg =""
            for flag in self.flags:
                if flagMsg !="":
                    flagMsg += "\n----"
                flagMsg += flag
                

            # This makes the flag string more readable in the confirm dialog
            message = ((f"Rom: {self.romText}\n"
                        f"Seed: {displaySeed}\n"
                        f"Mode: {self.mode}\n"
                        f"Flags: \n----{flagMsg}\n"
                        f"(Hyphens are not actually used in seed generation)"))
            messBox = QMessageBox.question(self, "Confirm Seed Generation?", message, QMessageBox.Yes| QMessageBox.Cancel)
            if messBox == 16384:  # User selects confirm/accept/yes option
                #finalFlags = self.flags.replace(" ", "")
                bundle = f"{self.version}.{self.mode}.{flagMode}.{self.seed}"
                # remove spam if the Randomizer asks for input
                # TODO: guify that stuff
                # Hash check can be moved out to when you pick the file.
                # If you delete the file between picking it and running, just spit out an error, no need to prompt.
                # Randomboost could send a signal ask for a number or whatever, but maybe it's better to just remove it or pick a fixed number?
                QtCore.pyqtRemoveInputHook()
                # TODO: put this in a new thread
                try:
                    result_file = Randomizer.randomize(args=['BeyondChaos.py', self.romText, bundle, "test"])
                #call(["py", "Randomizer.py", self.romText, bundle, "test"])
                # Running the Randomizer twice in one session doesn't work because of global state.
                # Exit so people don't try it.
                # TODO: fix global state then remove this
                except Exception as e:
                    traceback.print_exc()
                    QMessageBox.critical(self, "Error creating ROM", str(e), QMessageBox.Ok)
                else:
                    QMessageBox.information(self, "Successfully created ROM", f"Result file: {result_file}", QMessageBox.Ok)
                    return
                #sys.exit() Lets no longer sysexit anymore so we don't have to reopen each time. The user can close the gui.

    # read each dictionary and update text field showing flag codes based upon
    #    flags denoted as 'True'
    def updateFlagString(self):
        self.flagsChanging = True
        self.flagString.clear()
        temp = ""
        for x in range(0, len(self.flags)):
            flag = self.flags[x]
            temp+= flag
            temp+=" "
        self.flagString.setText(temp)
        self.flagsChanging=False

    # read through dictionaries and set flag checkboxes as 'checked'
    def updateFlagCheckboxes(self):
        for t, d in zip(self.tablist, self.dictionaries):
            # create a list of all checkbox objects from the current QTabWidget
            children = t.findChildren(FlagCheckBox)

            # enumerate checkbox objects and set them to 'checked' if corresponding
            #   flag value is true
            for c in children:
                value = c.value
                #print(value + str(d[value]['checked']))
                if d[value]['checked']:
                    c.setProperty('checked', True)
                else:
                    c.setProperty('checked', False)

    # when radio button is checked, update the main class variable
    def updateRadioSelection(self, mode):
        self.mode = mode

    # enumerate radio button objects and set them to the currently set mode variable
    def updateModeSelection(self):
        for i in self.middleLeftGroupBox.findChildren((QRadioButton)):
            if i.mode == self.mode:
                i.setProperty('checked', True)
                break

    # update list variable with data from currently loaded dictionaries
    def updateDictionaries(self):
        self.dictionaries = [self.flag, self.sprite, self.aesthetic, self.major,
                             self.experimental, self.gamebreaking, self.battle, self.beta]



if __name__ == "__main__":
    print("Loading GUI, checking for config file, updater file and updates please wait.")
    try:
        Update.configExists()
        App = QApplication(sys.argv)
        window = Window()
        time.sleep(3)
        sys.exit(App.exec())
    except Exception:
        traceback.print_exc()
