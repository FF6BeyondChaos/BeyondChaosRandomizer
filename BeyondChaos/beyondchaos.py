import sys
import time
import traceback

import musicrandomizer
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QPushButton, QCheckBox, QWidget, QVBoxLayout, QLabel, QGroupBox, \
    QHBoxLayout, QLineEdit, QComboBox, QFileDialog, QApplication, \
    QTabWidget, QInputDialog, QScrollArea, QMessageBox, QGraphicsDropShadowEffect

import character
import config
import esperrandomizer
import formationrandomizer
import itemrandomizer
import locationrandomizer
import monsterrandomizer
import chestrandomizer
import options
import randomizer
import towerrandomizer
import update
from importlib import reload

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
        self.width = 1000
        self.height = 700

        # values to be sent to Randomizer
        self.romText = ""
        self.version = "4"
        self.mode = "normal" # default
        self.seed = ""
        self.flags = []


        # dictionaries to hold flag data
        self.aesthetic = {}
        self.sprite = {}
        self.spriteCategories = {}
        self.experimental = {}
        self.gamebreaking = {}
        self.major = {}
        self.flag = {}
        self.battle = {}
        self.beta = {}
        self.dictionaries = [self.flag, self.sprite, self.spriteCategories, self.battle, self.aesthetic, self.major,
                              self.experimental, self.gamebreaking, self.beta]
        #keep a list of all checkboxes
        self.checkBoxes = []

        # array of supported game modes
        self.supportedGameModes = ["normal", "katn", "ancientcave", "speedcave", "racecave", "dragonhunt"]
        # dictionary of game modes for drop down
        self.GameModes = {}

        # array of preset flags and codes
        self.supportedPresets = ["newplayer", "intermediateplayer", "advancedplayer", "raceeasy", "racemedium", "raceinsane"]
        # dictionay of game presets from drop down
        self.GamePresets = {}

        #tabs names for the tabs in flags box
        self.tabNames = ["Flags", "Sprites", "SpriteCategories", "Battle", "Aesthetic", "Major", "Experimental", "Gamebreaking", "Beta"]

        # ui elements
        self.flagString = QLineEdit() #flag text box for displaying the flags
        self.comboBox = QComboBox() #flag saved preset dropdown
        self.modeBox = QComboBox() #game mode drop down to pick what gamemode
        self.presetBox = QComboBox() #official supported preset flags
        self.modeDescription = QLabel("Pick a Game Mode!")
        self.flagDescription = QLabel("Pick a Flag Set!")
        #tabs: Flags, Sprites, Battle, etc...
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()
        self.tab7 = QWidget()
        self.tab8 = QWidget()
        self.tab9 = QWidget()

        #self.middleLeftGroupBox = QGroupBox() #obsolted
        self.tablist = [self.tab1, self.tab2, self.tab3, self.tab4, self.tab5, self.tab6, self.tab7, self.tab8, self.tab9]

        #global busy notifications
        flagsChanging = False

        # ----------- Begin buiding program/window
        # ------------------------------

        # pull data from files
        self.initCodes()
        

        # create window using geometry data
        self.InitWindow()

        self.romInput.setText(self.romText)
        self.updateFlagString()
        self.updateFlagCheckboxes()
        self.flagButtonClicked()
        self.updatePresetDropdown()
        self.clearUI()          #clear the UI of all selections

    def InitWindow(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        
        # build the UI
        self.CreateLayout()

        # show program onscreen
        self.show()    #maximize the randomizer
        #self.showMaximized()    #maximize the randomizer
        
        index = self.presetBox.currentIndex()

        

    def CreateLayout(self):
        # Primary Vertical Box Layout
        vbox = QVBoxLayout()

        titleLabel = QLabel("Beyond Chaos Randomizer")
        font = QtGui.QFont("Arial", 24, QtGui.QFont.Black)
        titleLabel.setFont(font)
        titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        titleLabel.setMargin(10)
        vbox.addWidget(titleLabel)
        

        #select rom, set seed, generate button
        vbox.addWidget(self.GroupBoxOneLayout()) 
        #game mode, preset flag selections and description
        vbox.addWidget(self.GroupBoxTwoLayout()) # Adding second groupbox to the layout
        #flags box
        vbox.addWidget(self.flagBoxLayout()) # Adding second/middle groupbox

        self.setLayout(vbox)

    def update(self):
        update.update()
        QMessageBox.information(self, "Update Process", "Checking for updates, if found this will automatically close", QMessageBox.Ok)
        

    # Top groupbox consisting of ROM selection, and Seed number input
    def GroupBoxOneLayout(self):
        topGroupBox = QGroupBox()
        TopHBox = QHBoxLayout()
        width = 250
        height = 60
       

        romLabel = QLabel("ROM:")
        TopHBox.addWidget(romLabel)
        self.romInput = QLineEdit()
        self.romInput.setPlaceholderText("Required")
        self.romInput.setReadOnly(True)
        TopHBox.addWidget(self.romInput)

        browseButton = QPushButton("Browse")
        browseButton.setMaximumWidth(width)
        browseButton.setMaximumHeight(height)        
        browseButton.setStyleSheet("font:bold; font-size:18px; height:24px; background-color: #5A8DBE; color: #E4E4E4;")
        browseButton.clicked.connect(lambda: self.openFileChooser())
        browseButton.setCursor(QCursor(QtCore.Qt.PointingHandCursor))   
        browseEffect = QGraphicsDropShadowEffect()
        browseEffect.setBlurRadius(3)
        browseButton.setGraphicsEffect(browseEffect)
        TopHBox.addWidget(browseButton)

        # space is a small hack so the S isn't in shadow.
        seedLabel = QLabel(" Seed:")
        TopHBox.addWidget(seedLabel)
        self.seedInput = QLineEdit()
        self.seedInput.setPlaceholderText("Optional")
        TopHBox.addWidget(self.seedInput)

        generateButton = QPushButton("Generate Seed")       
        generateButton.setMaximumWidth(width)
        generateButton.setMaximumHeight(height)        
        generateButton.setStyleSheet("font:bold; font-size:18px; height:24px; background-color: #5A8DBE; color: #E4E4E4;")
        generateButton.clicked.connect(lambda: self.generateSeed())
        generateButton.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        generateEffect = QGraphicsDropShadowEffect()
        generateEffect.setBlurRadius(3)
        generateButton.setGraphicsEffect(generateEffect)
        TopHBox.addWidget(generateButton)

        topGroupBox.setLayout(TopHBox)

        return topGroupBox

    def GroupBoxTwoLayout(self):

        self.compileModes()
        self.compileSupportedPresets()
        vhbox = QVBoxLayout()
        groupBoxTwo = QGroupBox()
        topGroupBox = QGroupBox()
        bottomGroupBox = QGroupBox()
        topHBox = QHBoxLayout()
        bottomHBox = QHBoxLayout()
        topHBox.addStretch(0)
        bottomHBox.addStretch(0)
        

        # ---- Game Mode Drop Down ---- #
        gameModeLabel = QLabel("Game Mode")
        gameModeLabel.setMaximumWidth(60)
        topHBox.addWidget(gameModeLabel, alignment = QtCore.Qt.AlignLeft)
        for item in self.GameModes.items():
            self.modeBox.addItem(item[0])
        self.modeBox.currentTextChanged.connect(lambda: self.updateGameDescription())
        topHBox.addWidget(self.modeBox, alignment = QtCore.Qt.AlignLeft)
        
        # ---- Preset Flags Drop Down ---- #
        presetModeLabel = QLabel("Preset Flags")
        presetModeLabel.setMaximumWidth(60)
        topHBox.addWidget(presetModeLabel, alignment = QtCore.Qt.AlignRight)
        self.presetBox.addItem("Select a flagset")
        self.loadSavedFlags()
        for item in self.GamePresets.items():
            self.presetBox.addItem(item[0])
        
            
        self.presetBox.currentTextChanged.connect(lambda: self.updatePresetDropdown())
        topHBox.addWidget(self.presetBox,alignment = QtCore.Qt.AlignLeft)
        
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
        effect.setBlurRadius(3)
        updateButton.setGraphicsEffect(effect)
        topHBox.addWidget(updateButton,alignment = QtCore.Qt.AlignLeft)

        # ---- Mode Description ---- #
        gameModeDescriptionLabel = QLabel("Game Mode Description:")
        gameModeDescriptionLabel.setStyleSheet("font-size:14px; height:24px; color:#253340;")
        bottomHBox.addWidget(gameModeDescriptionLabel, alignment = QtCore.Qt.AlignLeft)
        self.modeDescription.setStyleSheet("font-size:14px; height:24px; color:#253340;")
        bottomHBox.addWidget(self.modeDescription, alignment = QtCore.Qt.AlignLeft)

        # ---- Spacer ---- #
        spacerDescriptionLabel = QLabel("          ")
        spacerDescriptionLabel.setStyleSheet("font-size:14px; height:24px; color:#253340;")
        bottomHBox.addWidget(spacerDescriptionLabel, alignment = QtCore.Qt.AlignLeft)

        # ---- Preset Description ---- #
        flagDescriptionLabel = QLabel("Flag Description:")
        flagDescriptionLabel.setStyleSheet("font-size:14px; height:24px; color:#253340;")
        bottomHBox.addWidget(flagDescriptionLabel, alignment = QtCore.Qt.AlignLeft)
        self.flagDescription.setStyleSheet("font-size:14px; height:24px; color:#253340;")
        bottomHBox.addWidget(self.flagDescription, alignment = QtCore.Qt.AlignLeft)

        topGroupBox.setLayout(topHBox)
        bottomGroupBox.setLayout(bottomHBox)
        vhbox.addWidget(topGroupBox)
        vhbox.addWidget(bottomGroupBox)
        groupBoxTwo.setLayout(vhbox)
        return groupBoxTwo


    def flagBoxLayout(self):
        groupBoxTwo = QGroupBox()
        middleHBox = QHBoxLayout()
        middleRightGroupBox = QGroupBox("Flag Selection")
        tabVBoxLayout = QVBoxLayout()
        tabs = QTabWidget()

        
        # loop to add tab objects to 'tabs' TabWidget
        for t, d, names in zip(self.tablist, self.dictionaries, self.tabNames):
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

        # this is the line in the layout that displays the string of selected flags
        #   and the button to save those flags
        widgetV = QWidget()
        widgetVBoxLayout = QVBoxLayout()
        widgetV.setLayout(widgetVBoxLayout)

        widgetVBoxLayout.addWidget(QLabel("Text-string of selected flags:"))
        self.flagString.textChanged.connect(self.textchanged)
        widgetVBoxLayout.addWidget(self.flagString)

        saveButton = QPushButton("Save flags selection")
        saveButton.clicked.connect(lambda: self.saveFlags())
        widgetVBoxLayout.addWidget(saveButton)

        # This part makes a group box and adds the selected-flags display
        #   and a button to clear the UI
        flagTextWidget = QGroupBox()
        flagTextHBox = QHBoxLayout()
        flagTextHBox.addWidget(widgetV)
        clearUiButton = QPushButton("Reset")
        clearUiButton.setStyleSheet("font-size:12px; height:60px")
        clearUiButton.clicked.connect(lambda: self.clearUI())
        flagTextHBox.addWidget(clearUiButton)
        flagTextWidget.setLayout(flagTextHBox)

        tabVBoxLayout.addWidget(flagTextWidget)
        middleRightGroupBox.setLayout(tabVBoxLayout)
        # ------------- Part two (right) end ---------------------------------------


        # add widgets to HBoxLayout and assign to middle groupbox layout
        middleHBox.addWidget(middleRightGroupBox)
        groupBoxTwo.setLayout(middleHBox)

        return groupBoxTwo

        

    # Middle groupbox of sub-groupboxes.  Consists of left section (game mode
    # selection)
    #   and right section (flag selection -> tab-sorted)
    def GroupBoxThreeLayout(self):
        groupBoxTwo = QGroupBox()
        middleHBox = QHBoxLayout()

        
        
        middleRightGroupBox = QGroupBox("Flag Selection")
        tabVBoxLayout = QVBoxLayout()
        tabs = QTabWidget()
        tabNames = ["Flags", "Sprites", "SpriteCategories", "Battle", "Aesthetic", "Major", "Experimental", "Gamebreaking", "Beta"]

        ############## Checkboxes and inline descriptions #####################

        #setStyleSheet("border:none");
        # loop to add tab objects to 'tabs' TabWidget
        for t, d, names in zip(self.tablist, self.dictionaries, tabNames):
            tabObj = QScrollArea()
            tabs.addTab(tabObj, names)
            #we have a horizontal box that can go item1, item 2 in left-right fashion
            itemLayout = QHBoxLayout()
            #we then have two vertical boxes, one for normal flags, one for flags that have sliders or entry boxes.
            boxOneLayout = QVBoxLayout()
            boxTwoVertLayout = QVBoxLayout()
            boxTwoHorzLayout = QVBoxLayout()
            #we then have the group boxes the vertical tayouts get set into
            groupOneBox = QGroupBox()
            groupTwoVertBox = QGroupBox()
            groupTwoHorzBox = QGroupBox()
            flagGroup = QGroupBox()
            for flagname, flagdesc in d.items():
                #TODO: this can probably be done better once I know GUI better...
                if flagname == "exp":
                    cbox = FlagCheckBox(f"{flagname}  -  {flagdesc['explanation']}", flagname)
                    #self.checkBoxes.append(cbox)
                    #cbox.clicked.connect(lambda checked: self.flagButtonClicked())
                    #boxTwoHorzLayout.addWidget(cbox)
                    #slider = QSlider(QtCore.Qt.Horizontal)
                    #boxTwoHorzLayout.addWidget(slider)
                    #groupTwoHorzBox.setLayout(boxTwoHorzLayout)
                    #boxTwoVertLayout.addWidget(groupTwoHorzBox)
                    #groupTwoHorzBox.setLayout(boxTwoVertLayout)
                else:
                    cbox = FlagCheckBox(f"{flagname}  -  {flagdesc['explanation']}", flagname)
                    self.checkBoxes.append(cbox)
                    cbox.clicked.connect(lambda checked: self.flagButtonClicked())
                    boxOneLayout.addWidget(cbox)                #context - adding a second pane to certain tabs for now for sliders.
                    groupOneBox.setLayout(boxOneLayout)
                itemLayout.addWidget(groupOneBox)
                #itemLayout.addWidget(groupTwoHorzBox)
            t.setLayout(itemLayout)
            #tablayout.addStretch(1)
            tabObj.setWidgetResizable(True)
            tabObj.setWidget(t)

        tabVBoxLayout.addWidget(tabs)
        #----------- tabs done ----------------------------

        # this is the line in the layout that displays the string of selected
        # flags
        #   and the button to save those flags
        widgetV = QWidget()
        widgetVBoxLayout = QVBoxLayout()
        widgetV.setLayout(widgetVBoxLayout)

        widgetVBoxLayout.addWidget(QLabel("Text-string of selected flags:"))
        self.flagString.textChanged.connect(self.textchanged)
        widgetVBoxLayout.addWidget(self.flagString)

        saveButton = QPushButton("Save flags selection")
        saveButton.clicked.connect(lambda: self.saveFlags())
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
        effect.setBlurRadius(3)
        clearUiButton.setGraphicsEffect(effect)
        flagTextHBox.addWidget(clearUiButton)
        flagTextWidget.setLayout(flagTextHBox)

        tabVBoxLayout.addWidget(flagTextWidget)
        middleRightGroupBox.setLayout(tabVBoxLayout)
        # ------------- Part two (right) end
        # ---------------------------------------


        # add widgets to HBoxLayout and assign to middle groupbox layout
        middleHBox.addWidget(middleRightGroupBox)
        groupBoxTwo.setLayout(middleHBox)

        return groupBoxTwo

  
                        

    # Bottom groupbox consisting of saved seeds selection box, and button to
    # generate seed
    def GroupBoxFourLayout(self):
        bottomGroupBox = QGroupBox()
        bottomHBox = QHBoxLayout()

        bottomHBox.addWidget(QLabel("Saved flag selection: "))

        #todo: Add amount of seeds to generate here.
        #todo: Add retry on failure checkbox
        bottomHBox.addStretch(1)


        bottomGroupBox.setLayout(bottomHBox)
        return bottomGroupBox

    # --------------------------------------------------------------------------------
    # -------------- NO MORE LAYOUT DESIGN PAST THIS POINT
    # ---------------------------
    # --------------------------------------------------------------------------------

    def textchanged(self, text):
        if (self.flagsChanging):
            return
        self.flagsChanging = True
        for c in self.checkBoxes:
            c.setChecked(False)
        values = text.split()
        self.flags.clear()
        self.flagString.clear()
        for v in values:
            for d in self.dictionaries:
                for flagname in d:
                    if v == flagname:
                        for c in self.checkBoxes:
                            if v == c.value:
                                c.setChecked(True)
                                self.flags.append(c.value)
                                self.updateFlagString()
        self.flagsChanging = False


    # (At startup) Opens reads code flags/descriptions and
    #   puts data into separate dictionaries
    def initCodes(self):
        for code in options.NORMAL_CODES + options.MAKEOVER_MODIFIER_CODES:
            if code.category == "aesthetic":
                d = self.aesthetic
            elif code.category == "sprite":
                d = self.sprite
            elif code.category == "spriteCategories":
                d = self.spriteCategories
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

        for flag in sorted(options.ALL_FLAGS):
            self.flag[flag.name] = {'explanation': flag.description, 'checked': True}


    # opens input dialog to get a name to assign a desired seed flagset, then
    # saves flags and selected mode to the cfg file
    def saveFlags(self):
        text, okPressed = QInputDialog.getText(self, "Save Seed", "Enter a name for this flagset", QLineEdit.Normal, "")
        if okPressed and text != '':
            self.GamePresets[text] = self.flagString.text()
            #flagString = self.flagString.text()
            #for flag in self.flags:
            #    flagString += flag + " "
            config.Writeflags(text, self.flagString.text())
            index = self.presetBox.findText(text)
            if index == -1:
                self.presetBox.addItem(text)
            else:
                self.presetBox.removeItem(index)
                self.presetBox.addItem(text)
            
            index = self.presetBox.findText(text)
            self.presetBox.setCurrentIndex(index)

    def loadSavedFlags(self):
        flagset = config.readFlags()
        if flagset != None:
            for text, flags in flagset.items():
                self.GamePresets[text] = flags


    # delete preset.  Dialog box confirms users choice to delete.  check is
    # done to ensure file
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
            if index == 0:
                if item[0] == "Normal":
                    self.modeDescription.setText(item[1])
                    self.mode = "normal"
            elif index == 1:
                if item[0] == "Race - Kefka @ Narshe":
                    self.modeDescription.setText(item[1])
                    self.mode = "katn"
            elif index == 2:
                if item[0] == "Ancient Cave":
                    self.modeDescription.setText(item[1])
                    self.mode = "ancientcave"
            elif index == 3:
                if item[0] == "Speed Cave":
                    self.modeDescription.setText(item[1])
                    self.mode = "speedcave"
            elif index == 4:
                if item[0] == "Race - Randomized Cave":
                    self.modeDescription.setText(item[1])
                    self.mode = "racecave"
            elif index == 5:
                if item[0] == "Race - Dragon Hunt":
                    self.modeDescription.setText(item[1])
                    self.mode = "dragonhunt"
            else:
                self.modeDescription.setText("Pick a Game Mode!")


    def updatePresetDropdown(self, index = -1):
        
        
        text = self.presetBox.currentText()
        index = self.presetBox.findText(text)
        flags = self.GamePresets.get(text)
        if index ==0:
            self.clearUI()
            self.flagDescription.clear()
            self.flagDescription.setText("Pick a flag set!")            
        elif index == 1:
            self.flagDescription.setText("Flags designed for a new player")
            self.flagString.setText(flags)
        elif index == 2:
            self.flagDescription.setText("Flags designed for an intermediate player")
            self.flagString.setText(flags)
        elif index == 3:
            self.flagDescription.setText("Flags designed for an advanced player")
            self.flagString.setText(flags)
        elif index == 4:
            self.flagDescription.setText("Flags designed for easy difficulty races")
            self.flagString.setText(flags)
        elif index == 5:
            self.flagDescription.setText("Flags designed for medium difficulty races")
            self.flagString.setText(flags)
        elif index == 6:
            self.flagDescription.setText("Flags designed for insane difficulty races")
            self.flagString.setText(flags)
        else:
            self.flagDescription.setText("Custom saved flags")
            self.flagString.setText(flags)
                
                
         
    def clearUI(self):
        self.seed = ""
        self.flags.clear
        self.seedInput.setText(self.seed)
        
        self.modeBox.setCurrentIndex(0)

        self.initCodes()
        self.updateFlagCheckboxes()
        self.flagButtonClicked()
        self.flagString.clear()
        self.flags.clear()
        self.updateGameDescription()
     
        

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
                        if flag == d[c.value]:
                            flagset = True
                    if flagset == False:
                        self.flags.append(c.value)
                else:
                    d[c.value]['checked'] = False
        #self.updateDictionaries()
        self.updateFlagString()


    # Opens file dialog to select rom file and assigns it to value in
    # parent/Window class
    def openFileChooser(self):
        file_path = QFileDialog.getOpenFileName(self, 'Open File', './',
                                                filter="ROMs (*.smc *.sfc *.fig);;All Files(*.*)")

        # display file location in text input field
        self.romInput.setText(str(file_path[0]))


    def compileModes(self):
        for mode in self.supportedGameModes:
            if mode == "normal":
                self.GameModes['Normal'] = "Play through the normal story with randomized gameplay."
            elif mode == "katn":
                self.GameModes['Race - Kefka @ Narshe'] = "Race through the story and defeat Kefka at Narshe"
            elif mode == "ancientcave":
                self.GameModes['Ancient Cave'] = "Play though a long randomized dungeon."
            elif mode == "speedcave":
                self.GameModes['Speed Cave'] = "Play through a medium randomized dungeon."
            elif mode == "racecave":
                self.GameModes['Race - Randomized Cave'] = "Race through a short randomized dungeon."
            elif mode == "dragonhunt":
                self.GameModes['Race - Dragon Hunt'] = "Race to kill all 8 dragons."

    def compileSupportedPresets(self):
        for mode in self.supportedPresets:
            if mode == "newplayer":
                self.GamePresets['New Player'] = "b c e g i m n o p q r s t w y z alasdraco capslockoff partyparty makeover johnnydmad"
            elif mode == "intermediateplayer":
                self.GamePresets['Intermediate Player'] = "b c d e g i j k l m n o p q r s t w y z alasdraco capslockoff makeover partyparty johnnydmad notawaiter mimetime"
            elif mode == "advancedplayer":
                self.GamePresets['Advanced Player'] = "b c d e f g i j k l m n o p q r s t u w y z alasdraco capslockoff johnnydmad makeover notawaiter partyparty dancingmaduin bsiab mimetime randombosses"
            elif mode == "raceeasy":
                self.GamePresets['Race - Easy'] = "b c d e f g i j k m n o p q r s t w y z capslockoff johnnydmad makeover notawaiter partyparty madworld"
            elif mode == "racemedium":
                self.GamePresets['Race - Medium'] = "b c d e f g i j k m n o p q r s t u w y z capslockoff johnnydmad makeover notawaiter partyparty electricboogaloo randombosses madworld"
            elif mode == "raceinsane":
                self.GamePresets['Race - Insane'] = "b c d e f g i j k m n o p q r s t u w y z capslockoff johnnydmad makeover notawaiter partyparty darkworld madworld bsiab electricboogaloo randombosses"

    # Get seed generation parameters from UI to prepare for seed generation
    # This will show a confirmation dialog, and call the local Randomizer.py
    # file
    #   and pass arguments to it
    def generateSeed(self):

        self.romText = self.romInput.text()
        if self.romText == "":  # Checks if user ROM is blank
            QMessageBox.about(self, "Error", "You need to select a FFVI rom!")
        else:
            self.seed = self.seedInput.text()

            displaySeed = self.seed

            flagMsg = ""

            if self.seed == "":
                displaySeed = "(none)" # pretty-printing :)

            flagMode = ""
            for flag in self.flags:
                flagMode += flag

                flagMsg = ""
            for flag in self.flags:
                if flagMsg != "":
                    flagMsg += "\n----"
                flagMsg += flag
            if flagMsg == "":
                QMessageBox.about(self, "Error", "You need to select a flag and/or code!")
                return

            # This makes the flag string more readable in the confirm dialog
            message = ((f"Rom: {self.romText}\n"
                        f"Seed: {displaySeed}\n"
                        f"Mode: {self.mode}\n"
                        f"Flags: \n----{flagMsg}\n"
                        f"(Hyphens are not actually used in seed generation)"))
            messBox = QMessageBox.question(self, "Confirm Seed Generation?", message, QMessageBox.Yes | QMessageBox.Cancel)
            if messBox == 16384:  # User selects confirm/accept/yes option
                #finalFlags = self.flags.replace(" ", "")
                bundle = f"{self.version}.{self.mode}.{flagMode}.{self.seed}"
                # remove spam if the Randomizer asks for input
                # TODO: guify that stuff
                # Hash check can be moved out to when you pick the file.
                # If you delete the file between picking it and running, just
                # spit out an error, no need to prompt.
                # Randomboost could send a signal ask for a number or whatever,
                # but maybe it's better to just remove it or pick a fixed
                # number?
                QtCore.pyqtRemoveInputHook()
                # TODO: put this in a new thread
                try:
                    result_file = randomizer.randomize(args=['beyondchaos.py', self.romText, bundle, "test"])
                # call(["py", "Randomizer.py", self.romText, bundle, "test"])
                # Running the Randomizer twice in one session doesn't work
                # because of global state.
                # Exit so people don't try it.
                # TODO: fix global state then remove this
                except Exception as e:
                    traceback.print_exc()
                    QMessageBox.critical(self, "Error creating ROM", str(e), QMessageBox.Ok)
                else:
                    QMessageBox.information(self, "Successfully created ROM", f"Result file: {result_file}", QMessageBox.Ok)
                    return
                finally:
                    reload(itemrandomizer)
                    reload(monsterrandomizer)
                    reload(formationrandomizer)
                    reload(character)
                    reload(esperrandomizer)
                    reload(locationrandomizer)
                    reload(musicrandomizer)
                    reload(towerrandomizer)
                    reload(chestrandomizer)
                #sys.exit() Lets no longer sysexit anymore so we don't have to
                #reopen each time.  The user can close the gui.

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
        self.flagsChanging = False

    # read through dictionaries and set flag checkboxes as 'checked'
    def updateFlagCheckboxes(self):
        for t, d in zip(self.tablist, self.dictionaries):
            # create a list of all checkbox objects from the current QTabWidget
            children = t.findChildren(FlagCheckBox)

            # enumerate checkbox objects and set them to 'checked' if
            # corresponding
            #   flag value is true
            for c in children:
                value = c.value
                #print(value + str(d[value]['checked']))
                if d[value]['checked']:
                    c.setProperty('checked', True)
                else:
                    c.setProperty('checked', False)



if __name__ == "__main__":
    print("Loading GUI, checking for config file, updater file and updates please wait.")
    try:
        update.configExists()
        App = QApplication(sys.argv)
        window = Window()
        time.sleep(3)
        sys.exit(App.exec())
    except Exception:
        traceback.print_exc()
