# Standard library imports
import configparser
import hashlib
import subprocess
import multiprocessing.process
import os
import sys
import time
import traceback

# Related third-party imports
from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import (QPushButton, QCheckBox, QWidget, QVBoxLayout,
                             QLabel, QGroupBox, QHBoxLayout, QLineEdit, QComboBox, QFileDialog,
                             QApplication, QTabWidget, QInputDialog, QScrollArea, QMessageBox,
                             QGraphicsDropShadowEffect, QGridLayout, QSpinBox, QDoubleSpinBox, QDialog,
                             QDialogButtonBox, QMenu, QMainWindow)

# Local application imports
import utils
import customthreadpool
from config import (readFlags, writeFlags)
from options import (ALL_FLAGS, NORMAL_CODES, MAKEOVER_MODIFIER_CODES, makeover_groups)
from update import (update_needed, get_updater)
from randomizer import randomize

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required. "
                    "Report this to https://github.com/FF6BeyondChaos/BeyondChaosRandomizer/issues")


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


class BingoPrompts(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WELCOME TO BEYOND CHAOS BINGO MODE")
        self.setMinimumWidth(600)
        self.abilities = False
        self.monsters = False
        self.items = False
        self.spells = False
        self.abilities_box = QCheckBox("Abilities", self)
        self.abilities_box.stateChanged.connect(self._toggle_abilities)
        self.monsters_box = QCheckBox("Monsters", self)
        self.monsters_box.stateChanged.connect(self._toggle_monsters)
        self.items_box = QCheckBox("Items", self)
        self.items_box.stateChanged.connect(self._toggle_items)
        self.spells_box = QCheckBox("Spells", self)
        self.spells_box.stateChanged.connect(self._toggle_spells)

        boxes_label = QLabel("Include what type of squares?", self)
        layout = QGridLayout(self)
        layout.addWidget(boxes_label)
        layout.addWidget(self.abilities_box)
        layout.addWidget(self.monsters_box)
        layout.addWidget(self.items_box)
        layout.addWidget(self.spells_box)

        self.grid_size = 5
        grid_size_label = QLabel("What size grid? (2-7)")
        self.grid_size_box = QSpinBox()
        self.grid_size_box.setRange(2, 7)
        self.grid_size_box.setValue(self.grid_size)
        self.grid_size_box.valueChanged.connect(self._set_grid_size)
        layout.addWidget(grid_size_label)
        layout.addWidget(self.grid_size_box)

        self.difficulty = "n"
        difficulty_label = QLabel("What difficulty level?")
        self.difficulty_dropdown = QComboBox(self)
        for difficulty in ["Easy", "Normal", "Hard"]:
            self.difficulty_dropdown.addItem(difficulty)
        self.difficulty_dropdown.setCurrentIndex(1)  # Normal
        self.difficulty_dropdown.currentTextChanged.connect(self._set_difficulty)
        layout.addWidget(difficulty_label)
        layout.addWidget(self.difficulty_dropdown)

        self.num_cards = 1
        num_cards_label = QLabel("Generate how many cards?")
        self.num_cards_box = QSpinBox()
        self.num_cards_box.setValue(self.num_cards)
        self.num_cards_box.valueChanged.connect(self._set_num_cards)
        layout.addWidget(num_cards_label)
        layout.addWidget(self.num_cards_box)

        button_box = QDialogButtonBox(self)
        button_box.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setOrientation(QtCore.Qt.Horizontal)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        button_box.button(QDialogButtonBox.Cancel)
        layout.addWidget(button_box)

    def _toggle_abilities(self):
        self.abilities = not self.abilities
        self.ok_button.setEnabled(self._get_is_ok_enabled())

    def _toggle_monsters(self):
        self.monsters = not self.monsters
        self.ok_button.setEnabled(self._get_is_ok_enabled())

    def _toggle_items(self):
        self.items = not self.items
        self.ok_button.setEnabled(self._get_is_ok_enabled())

    def _toggle_spells(self):
        self.spells = not self.spells
        self.ok_button.setEnabled(self._get_is_ok_enabled())

    def _set_grid_size(self):
        self.grid_size = self.grid_size_box.value()

    def _set_difficulty(self, value):
        self.difficulty = value[0].lower()

    def _set_num_cards(self):
        self.num_cards = self.num_cards_box.value()

    def _get_is_ok_enabled(self):
        return self.spells or self.items or self.monsters or self.abilities


def update_bc():
    update_message = QMessageBox()
    update_message.setWindowTitle("Beyond Chaos Updater")
    update_message.setText("Beyond Chaos will check for updates to the core randomizer, character sprites, "
                           "monster sprites. If updates are performed, BeyondChaos.exe will automatically close.")
    update_message.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
    button_clicked = update_message.exec()
    if button_clicked == QMessageBox.Ok:
        args = ["-pid " + str(os.getpid())]
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Starting Beyond Chaos Updater...\n")
        try:
            subprocess.Popen(args=args, executable="BeyondChaosUpdater.exe")
        except FileNotFoundError:
            get_updater()
            subprocess.Popen(args=args, executable="BeyondChaosUpdater.exe")


class Window(QMainWindow):
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
        self.romOutputDirectory = ""
        self.version = "3"
        self.mode = "normal"
        self.seed = ""
        self.flags = []
        self.bingotype = []
        self.bingosize = 5
        self.bingodiff = ""
        self.bingocards = 1

        # dictionaries to hold flag data
        self.aesthetic = {}
        self.sprite = {}
        self.spriteCategories = {}
        self.experimental = {}
        self.gamebreaking = {}
        self.field = {}
        self.characters = {}
        self.flag = {}
        self.battle = {}
        self.beta = {}
        self.dictionaries = [
            self.flag, self.sprite, self.spriteCategories, self.battle,
            self.aesthetic, self.field, self.characters, self.experimental, self.gamebreaking,
            self.beta
        ]
        # keep a list of all checkboxes
        self.checkBoxes = []

        # array of supported game modes
        self.supportedGameModes = [
            "normal", "katn", "ancientcave", "speedcave", "racecave",
            "dragonhunt"
        ]
        # dictionary of game modes for drop down
        self.GameModes = {}

        # array of preset flags and codes
        self.supportedPresets = [
            "newplayer", "intermediateplayer", "advancedplayer", "raceeasy",
            "racemedium", "raceinsane"
        ]
        # dictionary of game presets from drop down
        self.GamePresets = {}

        # tabs names for the tabs in flags box
        self.tabNames = [
            "Flags", "Sprites", "SpriteCategories", "Battle", "Aesthetic",
            "Field", "Characters", "Experimental", "Gamebreaking", "Beta"
        ]

        # ui elements
        self.flagString = QLineEdit()
        self.modeBox = QComboBox()
        self.presetBox = QComboBox()
        self.modeDescription = QLabel("Pick a Game Mode!")
        self.flagDescription = QLabel("Pick a Flag Set!")

        # tabs: Flags, Sprites, Battle, etc...
        self.central_widget = QWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab4 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()
        self.tab7 = QWidget()
        self.tab8 = QWidget()
        self.tab9 = QWidget()

        self.tablist = [
            self.tab1, self.tab2, self.tab3, self.tab4, self.tab5, self.tab6,
            self.tab7, self.tab8, self.tab9
        ]

        # global busy notifications
        self.flagsChanging = False

        # Begin buiding program/window
        # pull data from files
        self.initCodes()

        # create window using geometry data
        self.initWindow()

        self.romInput.setText(self.romText)
        self.romOutput.setText(self.romOutputDirectory)
        self.updateFlagString()
        self.updateFlagCheckboxes()
        self.flagButtonClicked()
        self.updatePresetDropdown()
        self.clearUI()

    def initWindow(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # build the UI
        self.createLayout()

        previousRomPath = ""
        previousOutputDirectory = ""

        try:
            config = configparser.ConfigParser()
            config.read('bcce.cfg')
            if 'ROM' in config:
                previousRomPath = config['ROM']['Path']
                previousOutputDirectory = config['ROM']['Output']
        except (IOError, KeyError):
            pass

        self.romText = previousRomPath
        self.romOutputDirectory = previousOutputDirectory

        # show program onscreen
        self.show()  # maximize the randomizer

        index = self.presetBox.currentIndex()

    def createLayout(self):
        # Menubar
        file_menu = QMenu("File", self)
        file_menu.addAction("Quit", App.quit)
        self.menuBar().addMenu(file_menu)

        self.menuBar().addAction("Update", update_bc)

        # Primary Vertical Box Layout
        vbox = QVBoxLayout()

        titleLabel = QLabel("Beyond Chaos Randomizer")
        font = QtGui.QFont("Arial", 24, QtGui.QFont.Black)
        titleLabel.setFont(font)
        titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        titleLabel.setMargin(10)
        vbox.addWidget(titleLabel)

        # rom input and output, seed input, generate button
        vbox.addWidget(self.GroupBoxOneLayout())
        # game mode, preset flag selections and description
        vbox.addWidget(self.GroupBoxTwoLayout())
        # flags box
        vbox.addWidget(self.flagBoxLayout())

        self.central_widget.setLayout(vbox)
        self.setCentralWidget(self.central_widget)

    # Top groupbox consisting of ROM selection, and Seed number input
    def GroupBoxOneLayout(self):
        groupLayout = QGroupBox("Input and Output")

        gridLayout = QGridLayout()

        # ROM INPUT
        labelRomInput = QLabel("ROM File:")
        labelRomInput.setAlignment(QtCore.Qt.AlignRight |
                                   QtCore.Qt.AlignVCenter)
        gridLayout.addWidget(labelRomInput, 1, 1)

        self.romInput = QLineEdit()
        self.romInput.setPlaceholderText("Required")
        self.romInput.setReadOnly(True)
        gridLayout.addWidget(self.romInput, 1, 2, 1, 3)

        btnRomInput = QPushButton("Browse")
        btnRomInput.setMaximumWidth(self.width)
        btnRomInput.setMaximumHeight(self.height)
        btnRomInput.setStyleSheet(
            "font:bold;"
            "font-size:18px;"
            "height:24px;"
            "background-color: #5A8DBE;"
            "color:#E4E4E4;"
        )
        btnRomInput.clicked.connect(lambda: self.openFileChooser())
        btnRomInput.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        btnRomInputStyle = QGraphicsDropShadowEffect()
        btnRomInputStyle.setBlurRadius(3)
        btnRomInputStyle.setOffset(3, 3)
        btnRomInput.setGraphicsEffect(btnRomInputStyle)
        gridLayout.addWidget(btnRomInput, 1, 5)

        # ROM OUTPUT
        lblRomOutput = QLabel("Output Directory:")
        lblRomOutput.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        gridLayout.addWidget(lblRomOutput, 2, 1)

        self.romOutput = QLineEdit()
        self.romInput.textChanged[str].connect(self.updateRomOutputPlaceholder)
        gridLayout.addWidget(self.romOutput, 2, 2, 1, 3)

        btnRomOutput = QPushButton("Browse")
        btnRomOutput.setMaximumWidth(self.width)
        btnRomOutput.setMaximumHeight(self.height)
        btnRomOutput.setStyleSheet(
            "font:bold;"
            "font-size:18px;"
            "height:24px;"
            "background-color:#5A8DBE;"
            "color:#E4E4E4;"
        )
        btnRomOutput.clicked.connect(lambda: self.openDirectoryChooser())
        btnRomOutput.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        btnRomOutputStyle = QGraphicsDropShadowEffect()
        btnRomOutputStyle.setBlurRadius(3)
        btnRomOutputStyle.setOffset(3, 3)
        btnRomOutput.setGraphicsEffect(btnRomOutputStyle)
        gridLayout.addWidget(btnRomOutput, 2, 5)

        # SEED INPUT
        lblSeedInput = QLabel("Seed Number:")
        lblSeedInput.setAlignment(QtCore.Qt.AlignRight |
                                  QtCore.Qt.AlignVCenter)
        gridLayout.addWidget(lblSeedInput, 3, 1)

        self.seedInput = QLineEdit()
        self.seedInput.setPlaceholderText("Optional")
        gridLayout.addWidget(self.seedInput, 3, 2)

        lblSeedCount = QLabel("Number to Generate:")
        lblSeedCount.setAlignment(QtCore.Qt.AlignRight |
                                  QtCore.Qt.AlignVCenter)
        gridLayout.addWidget(lblSeedCount, 3, 3)

        self.seedCount = QSpinBox()
        self.seedCount.setValue(1)
        self.seedCount.setMinimum(1)
        self.seedCount.setMaximum(99)
        self.seedCount.setFixedWidth(40)
        gridLayout.addWidget(self.seedCount, 3, 4)

        btnGenerate = QPushButton("Generate")
        btnGenerate.setMinimumWidth(125)
        btnGenerate.setMaximumWidth(self.width)
        btnGenerate.setMaximumHeight(self.height)
        btnGenerate.setStyleSheet(
            "font:bold;"
            "font-size:18px;"
            "height:24px;"
            "background-color:#5A8DBE;"
            "color:#E4E4E4;"
        )
        btnGenerate.clicked.connect(lambda: self.generateSeed())
        btnGenerate.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        btnGenerateStyle = QGraphicsDropShadowEffect()
        btnGenerateStyle.setBlurRadius(3)
        btnGenerateStyle.setOffset(3, 3)
        btnGenerate.setGraphicsEffect(btnGenerateStyle)
        gridLayout.addWidget(btnGenerate, 3, 5)

        groupLayout.setLayout(gridLayout)
        return groupLayout

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
        topHBox.addWidget(gameModeLabel, alignment=QtCore.Qt.AlignLeft)
        for item in self.GameModes.items():
            self.modeBox.addItem(item[0])
        self.modeBox.currentTextChanged.connect(
            lambda: self.updateGameDescription()
        )
        topHBox.addWidget(self.modeBox, alignment=QtCore.Qt.AlignLeft)

        # ---- Preset Flags Drop Down ---- #
        presetModeLabel = QLabel("Preset Flags")
        presetModeLabel.setMaximumWidth(60)
        topHBox.addWidget(presetModeLabel, alignment=QtCore.Qt.AlignRight)
        self.presetBox.addItem("Select a flagset")
        self.loadSavedFlags()
        for item in self.GamePresets.items():
            self.presetBox.addItem(item[0])

        self.presetBox.currentTextChanged.connect(
            lambda: self.updatePresetDropdown()
        )
        topHBox.addWidget(self.presetBox, alignment=QtCore.Qt.AlignLeft)

        # ---- Update Button ---- #
        # updateButton = QPushButton("Check for Updates")
        # updateButton.setStyleSheet(
        #    "font:bold;"
        #    "font-size:18px;"
        #    "height:24px;"
        #    "background-color:#5A8DBE;"
        #    "color:#E4E4E4;")
        # width = 250
        # height = 60
        # updateButton.setMaximumWidth(width)
        # updateButton.setMaximumHeight(height)
        # updateButton.clicked.connect(lambda: self.update_bc())
        # updateButton.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        # effect = QGraphicsDropShadowEffect()
        # effect.setBlurRadius(3)
        # updateButton.setGraphicsEffect(effect)
        # topHBox.addWidget(
        #    updateButton, 
        #    alignment = QtCore.Qt.AlignLeft
        # )

        # ---- Mode Description ---- #
        gameModeDescriptionLabel = QLabel("Game Mode Description:")
        gameModeDescriptionLabel.setStyleSheet(
            "font-size:14px; "
            "height:24px;"
            "color:#253340;"
        )
        bottomHBox.addWidget(
            gameModeDescriptionLabel,
            alignment=QtCore.Qt.AlignLeft
        )
        self.modeDescription.setStyleSheet(
            "font-size:14px;"
            "height:24px;"
            "color:#253340;"
        )
        bottomHBox.addWidget(
            self.modeDescription,
            alignment=QtCore.Qt.AlignLeft
        )

        # ---- Spacer ---- #
        spacerDescriptionLabel = QLabel("          ")
        spacerDescriptionLabel.setStyleSheet(
            "font-size:14px;"
            "height:24px;"
            "color:#253340;"
        )
        bottomHBox.addWidget(
            spacerDescriptionLabel,
            alignment=QtCore.Qt.AlignLeft
        )

        # ---- Preset Description ---- #
        flagDescriptionLabel = QLabel("Flag Description:")
        flagDescriptionLabel.setStyleSheet(
            "font-size:14px;"
            "height:24px;"
            "color:#253340;"
        )
        bottomHBox.addWidget(
            flagDescriptionLabel,
            alignment=QtCore.Qt.AlignLeft
        )
        self.flagDescription.setStyleSheet(
            "font-size:14px;"
            "height:24px;"
            "color:#253340;"
        )
        bottomHBox.addWidget(
            self.flagDescription,
            alignment=QtCore.Qt.AlignLeft
        )

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
        for t, d, names in zip(self.tablist,
                               self.dictionaries,
                               self.tabNames):
            tabObj = QScrollArea()
            tabs.addTab(tabObj, names)
            tablayout = QGridLayout()
            currentRow = 0
            for flagname, flagdesc in d.items():
                if flagdesc['inputtype'] == 'checkbox':
                    cbox = FlagCheckBox(
                        f"{flagname}  -  {flagdesc['explanation']}",
                        flagname
                    )
                    self.checkBoxes.append(cbox)
                    tablayout.addWidget(cbox, currentRow, 1, 1, 2)
                    cbox.clicked.connect(lambda checked: self.flagButtonClicked())
                elif flagdesc['inputtype'] == 'numberbox':
                    if flagname in ['expboost', 'gpboost', 'mpboost']:
                        nbox = QDoubleSpinBox()
                    else:
                        nbox = QSpinBox()


                    if flagname == "cursepower":
                        nbox.setMinimum(0)
                        nbox.setSpecialValueText("Random")
                        nbox.setMaximum(255)
                        nbox.default = 255
                    elif flagname in ['expboost', 'gpboost', 'mpboost']:
                        nbox.setMinimum(-0.1)
                        nbox.setSingleStep(.1)
                        nbox.setSpecialValueText('Off')
                        nbox.setSuffix("x")
                        nbox.default = nbox.minimum()
                    else:
                        nbox.setMinimum(-1)
                        nbox.setSpecialValueText('Off')
                        nbox.default = nbox.minimum()

                    nbox.setFixedWidth(70)
                    nbox.setValue(nbox.default)
                    nbox.text = flagname
                    flaglbl = QLabel(f"{flagname}  -  {flagdesc['explanation']}")
                    tablayout.addWidget(nbox, currentRow, 1)
                    tablayout.addWidget(flaglbl, currentRow, 2)
                    nbox.valueChanged.connect(lambda: self.flagButtonClicked())
                elif flagdesc['inputtype'] == 'combobox':
                    cmbbox = QComboBox()
                    cmbbox.addItems(flagdesc['choices'])
                    width = 50
                    for choice in flagdesc['choices']:
                        width = max(width, len(choice) * 10)
                    cmbbox.setFixedWidth(width)
                    cmbbox.text = flagname
                    if makeover_groups and flagname in makeover_groups:
                        cmbbox.setCurrentIndex(cmbbox.findText("Normal"))
                        flaglbl = QLabel(f"{flagname} (" + str(makeover_groups[flagname]) +
                                         ")   -  " + f"{flagdesc['explanation']}")
                    else:
                        cmbbox.setCurrentIndex(cmbbox.findText("Vanilla"))
                        flaglbl = QLabel(f"{flagname}  -  {flagdesc['explanation']}")
                    tablayout.addWidget(cmbbox, currentRow, 1)
                    tablayout.addWidget(flaglbl, currentRow, 2)
                    cmbbox.activated[str].connect(lambda: self.flagButtonClicked())
                currentRow += 1

            t.setLayout(tablayout)
            tabObj.setWidgetResizable(True)
            tabObj.setWidget(t)

        tabVBoxLayout.addWidget(tabs)

        # This is the line in the layout that displays the string 
        # of selected flags and the button to save those flags
        widgetV = QWidget()
        widgetVBoxLayout = QVBoxLayout()
        widgetV.setLayout(widgetVBoxLayout)

        widgetVBoxLayout.addWidget(QLabel("Text-string of selected flags:"))
        self.flagString.textChanged.connect(self.textchanged)
        widgetVBoxLayout.addWidget(self.flagString)

        saveButton = QPushButton("Save flags selection")
        saveButton.clicked.connect(lambda: self.saveFlags())
        widgetVBoxLayout.addWidget(saveButton)

        # This part makes a group box and adds the selected-flags 
        # display and a button to clear the UI
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
        # ------------- Part two (right) end ------------------------

        # Add widgets to HBoxLayout and assign to middle groupbox
        # layout
        middleHBox.addWidget(middleRightGroupBox)
        groupBoxTwo.setLayout(middleHBox)

        return groupBoxTwo

    # Middle groupbox of sub-groupboxes.  Consists of left section
    # (game mode # selection) and right section 
    # (flag selection -> tab-sorted)
    def GroupBoxThreeLayout(self):
        groupBoxTwo = QGroupBox()
        middleHBox = QHBoxLayout()

        middleRightGroupBox = QGroupBox("Flag Selection")
        tabVBoxLayout = QVBoxLayout()
        tabs = QTabWidget()
        tabNames = [
            "Flags", "Sprites", "SpriteCategories", "Battle", "Aesthetic",
            "Field", "Characters", "Experimental", "Gamebreaking", "Beta"
        ]

        ########## Checkboxes and inline descriptions ###########

        # loop to add tab objects to 'tabs' TabWidget
        for t, d, names in zip(self.tablist, self.dictionaries, tabNames):
            tabObj = QScrollArea()
            tabs.addTab(tabObj, names)
            # We have a horizontal box that can go item1, 
            # item 2 in left-right fashion
            itemLayout = QHBoxLayout()
            # We then have two vertical boxes, one for normal flags, 
            # one for flags that have sliders or entry boxes.
            boxOneLayout = QVBoxLayout()
            boxTwoVertLayout = QVBoxLayout()
            boxTwoHorzLayout = QVBoxLayout()
            # We then have the group boxes the vertical tayouts get 
            # set into
            groupOneBox = QGroupBox()
            groupTwoVertBox = QGroupBox()
            groupTwoHorzBox = QGroupBox()
            flagGroup = QGroupBox()
            for flagname, flagdesc in d.items():
                # TODO: this can probably be done better once I 
                # know GUI better...
                if flagname == "exp":
                    cbox = FlagCheckBox(
                        f"{flagname}  -  {flagdesc['explanation']}",
                        flagname
                    )
                else:
                    cbox = FlagCheckBox(
                        f"{flagname}  -  {flagdesc['explanation']}",
                        flagname
                    )
                    self.checkBoxes.append(cbox)
                    cbox.clicked.connect(
                        lambda checked: self.flagButtonClicked()
                    )
                    # Context - adding a second pane to certain tabs 
                    # for now for sliders.
                    boxOneLayout.addWidget(cbox)
                    groupOneBox.setLayout(boxOneLayout)
                itemLayout.addWidget(groupOneBox)
            t.setLayout(itemLayout)
            tabObj.setWidgetResizable(True)
            tabObj.setWidget(t)

        tabVBoxLayout.addWidget(tabs)
        # ----------- tabs done --------------

        # This is the line in the layout that displays the string 
        # of selected flags and the button to save those flags
        widgetV = QWidget()
        widgetVBoxLayout = QVBoxLayout()
        widgetV.setLayout(widgetVBoxLayout)

        widgetVBoxLayout.addWidget(QLabel("Text-string of selected flags:"))
        self.flagString.textChanged.connect(self.textchanged)
        widgetVBoxLayout.addWidget(self.flagString)

        saveButton = QPushButton("Save flags selection")
        saveButton.clicked.connect(lambda: self.saveFlags())
        widgetVBoxLayout.addWidget(saveButton)

        # This part makes a group box and adds the selected-flags 
        # display and a button to clear the UI
        flagTextWidget = QGroupBox()
        flagTextHBox = QHBoxLayout()
        flagTextHBox.addWidget(widgetV)
        clearUiButton = QPushButton("Reset")
        clearUiButton.setStyleSheet(
            "font:bold;"
            "font-size:16px;"
            "height:60px;"
            "background-color:#5A8DBE;"
            "color:#E4E4E4;"
        )
        clearUiButton.clicked.connect(lambda: self.clearUI())
        clearUiButton.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(3)
        effect.setOffset(3, 3)
        clearUiButton.setGraphicsEffect(effect)
        flagTextHBox.addWidget(clearUiButton)
        flagTextWidget.setLayout(flagTextHBox)

        tabVBoxLayout.addWidget(flagTextWidget)
        middleRightGroupBox.setLayout(tabVBoxLayout)
        # ------------- Part two (right) end-------------------------

        # Add widgets to HBoxLayout and assign to middle groupbox 
        # layout
        middleHBox.addWidget(middleRightGroupBox)
        groupBoxTwo.setLayout(middleHBox)

        return groupBoxTwo

    # Bottom groupbox consisting of saved seeds selection box, and 
    # button to generate seed
    def GroupBoxFourLayout(self):
        bottomGroupBox = QGroupBox()
        bottomHBox = QHBoxLayout()

        bottomHBox.addWidget(QLabel("Saved flag selection: "))

        # todo: Add amount of seeds to generate here.
        # todo: Add retry on failure checkbox
        bottomHBox.addStretch(1)

        bottomGroupBox.setLayout(bottomHBox)
        return bottomGroupBox

    # ---------------------------------------------------------------
    # ------------ NO MORE LAYOUT DESIGN PAST THIS POINT-------------
    # ---------------------------------------------------------------

    def textchanged(self, text):
        if (self.flagsChanging):
            return
        self.flagsChanging = True
        self.clear_controls()
        values = text.split()
        self.flags.clear()
        self.flagString.clear()
        children = []
        for t in self.tablist:
            children.extend(t.children())
        for child in children:
            for v in values:
                v = str(v).lower()
                if type(child) == FlagCheckBox and v == child.value:
                    child.setChecked(True)
                    self.flags.append(v)
                elif type(child) in [QSpinBox] and str(v).startswith(child.text.lower()):
                    if ":" in v:
                        try:
                            child.setValue(int(str(v).split(":")[1]))
                            self.flags.append(v)
                        except ValueError:
                            pass
                elif type(child) in [QDoubleSpinBox] and str(v).startswith(child.text.lower()):
                    if ":" in v:
                        try:
                            child.setValue(float(str(v).split(":")[1]))
                            self.flags.append(v)
                        except ValueError:
                            pass
                elif type(child) in [QComboBox] and str(v).startswith(child.text.lower()):
                    if ":" in v:
                        index_of_value = child.findText(str(v).split(":")[1], QtCore.Qt.MatchFixedString)
                        if index_of_value > 0:
                            child.setCurrentIndex(index_of_value)
                            self.flags.append(v)
        self.updateFlagString()
        self.flagsChanging = False

    # (At startup) Opens reads code flags/descriptions and
    #   puts data into separate dictionaries
    def initCodes(self):
        for code in NORMAL_CODES + MAKEOVER_MODIFIER_CODES:
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
            elif code.category == "field":
                d = self.field
            elif code.category == "characters":
                d = self.characters
            elif code.category == "beta":
                d = self.beta
            elif code.category == "battle":
                d = self.battle
            else:
                print(f"Code {code.name} does not have a valid category.")
                continue

            d[code.name] = {
                'explanation': code.long_description,
                'inputtype': code.inputtype,
                'checked': False,
                'choices': code.choices
            }

        for flag in sorted(ALL_FLAGS):
            self.flag[flag.name] = {
                'explanation': flag.description,
                'inputtype': flag.inputtype,
                'checked': True
            }

    # opens input dialog to get a name to assign a desired seed flagset, then
    # saves flags and selected mode to the cfg file
    def saveFlags(self):
        text, okPressed = QInputDialog.getText(
            self,
            "Save Seed",
            "Enter a name for this flagset",
            QLineEdit.Normal,
            ""
        )
        if okPressed and text != '':
            self.GamePresets[text] = (
                    self.flagString.text() + "|" + self.mode
            )
            writeFlags(
                text,
                (self.flagString.text() + "|" + self.mode)
            )
            index = self.presetBox.findText(text)
            if index == -1:
                self.presetBox.addItem(text)
            else:
                self.presetBox.removeItem(index)
                self.presetBox.addItem(text)

            index = self.presetBox.findText(text)
            self.presetBox.setCurrentIndex(index)

    def loadSavedFlags(self):
        flagset = readFlags()
        if flagset != None:
            for text, flags in flagset.items():
                self.GamePresets[text] = flags

    def updateGameDescription(self):
        self.modeDescription.clear()
        modes = {0: ("Normal", "normal"),
                 1: ("Race - Kefka @ Narshe", "katn"),
                 2: ("Ancient Cave", "ancientcave"),
                 3: ("Speed Cave", "speedcave"),
                 4: ("Race - Randomized Cave", "racecave"),
                 5: ("Race - Dragon Hunt", "dragonhunt"),
                 }
        index = self.modeBox.currentIndex()
        self.modeDescription.setText(modes.get(index, "Pick a Game Mode!")[0])
        self.mode = \
            [x[1] for x in modes.values() if x[1] == modes.get(index)[1]][0]

    def updatePresetDropdown(self, index=-1):

        modes = {0: ("Normal", "normal"),
                 1: ("Race - Kefka @ Narshe", "katn"),
                 2: ("Ancient Cave", "ancientcave"),
                 3: ("Speed Cave", "speedcave"),
                 4: ("Race - Randomized Cave", "racecave"),
                 5: ("Race - Dragon Hunt", "dragonhunt")}
        text = self.presetBox.currentText()
        index = self.presetBox.findText(text)
        flags = self.GamePresets.get(text)
        if index == 0:
            self.clearUI()
            self.flagDescription.clear()
            self.flagDescription.setText("Pick a flag set!")
        elif index == 1:
            self.flagDescription.setText("Flags designed for a new player")
            self.flagString.setText(flags)
            self.mode = "normal"
            self.modeBox.setCurrentIndex(0)
        elif index == 2:
            self.flagDescription.setText(
                "Flags designed for an intermediate player"
            )
            self.flagString.setText(flags)
            self.mode = "normal"
            self.modeBox.setCurrentIndex(0)
        elif index == 3:
            self.flagDescription.setText(
                "Flags designed for an advanced player"
            )
            self.flagString.setText(flags)
            self.mode = "normal"
            self.modeBox.setCurrentIndex(0)
        elif index == 4:
            self.flagDescription.setText(
                "Flags designed for KaN easy difficulty races"
            )
            self.flagString.setText(flags)
            self.mode = "katn"
            self.modeBox.setCurrentIndex(1)
        elif index == 5:
            self.flagDescription.setText(
                "Flags designed for KaN medium difficulty races"
            )
            self.flagString.setText(flags)
            self.mode = "katn"
            self.modeBox.setCurrentIndex(1)
        elif index == 6:
            self.flagDescription.setText(
                "Flags designed for KaN insane difficulty races"
            )
            self.flagString.setText(flags)
            self.mode = "katn"
            self.modeBox.setCurrentIndex(1)
        else:
            customflags = flags.split("|")[0]
            mode = flags.split("|")[1]
            self.flagDescription.setText("Custom saved flags")
            self.flagString.setText(customflags)
            self.mode = mode
            self.modeBox.setCurrentIndex(
                [k for k, v in modes.items() if v[1] == mode][0]
            )

    def clearUI(self):
        self.seed = ""
        self.flags.clear()
        self.seedInput.setText(self.seed)

        self.modeBox.setCurrentIndex(0)
        self.presetBox.setCurrentIndex(0)
        self.initCodes()
        self.updateFlagCheckboxes()
        self.flagButtonClicked()
        self.flagString.clear()
        self.flags.clear()
        self.updateGameDescription()

    def clear_controls(self):
        for tab in self.tablist:
            for child in tab.children():
                if type(child) == FlagCheckBox:
                    child.setChecked(False)
                elif type(child) == QSpinBox or type(child) == QDoubleSpinBox:
                    child.setValue(child.default)
                elif type(child) == QComboBox:
                    if makeover_groups and child.text in makeover_groups:
                        child.setCurrentIndex(child.findText("Normal"))
                    else:
                        child.setCurrentIndex(child.findText("Vanilla"))

    # When flag UI button is checked, update corresponding
    # dictionary values
    def flagButtonClicked(self):
        # Check self.flagsChanging first. If that is set, a new flag preset has been selected, which is causing
        #  the controls to change and call this method. But we do not want to do anything then, otherwise it can
        #  add duplicate entries to the flag string
        if not self.flagsChanging:
            self.flags.clear()
            for t, d in zip(self.tablist, self.dictionaries):
                children = t.findChildren(FlagCheckBox)
                for c in children:
                    if c.isChecked():
                        d[c.value]['checked'] = True
                        self.flags.append(c.value)
                    else:
                        d[c.value]['checked'] = False
                children = t.findChildren(QSpinBox) + t.findChildren(QDoubleSpinBox)
                for c in children:
                    if not round(c.value(), 1) == c.default:
                        if c.text == "cursepower" and c.value() == 0:
                            self.flags.append(c.text + ":random")
                        else:
                            self.flags.append(c.text + ":" + str(round(c.value(), 2)))
                children = t.findChildren(QComboBox)
                for c in children:
                    if c.currentText() not in ["Vanilla", "Normal"]:
                        self.flags.append(c.text.lower() + ":" + c.currentText().lower())

            self.updateFlagString()

    # Opens file dialog to select rom file and assigns it to value in
    # parent/Window class
    def openFileChooser(self):
        file_path = QFileDialog.getOpenFileName(
            self,
            'Open File',
            './',
            filter="ROMs (*.smc *.sfc *.fig);;All Files(*.*)"
        )

        # display file location in text input field
        self.romInput.setText(str(file_path[0]))

    def openDirectoryChooser(self):
        file_path = QFileDialog.getExistingDirectory(self, 'Open File', './')

        # display file location in text input field
        self.romOutput.setText(str(file_path))

    def compileModes(self):
        for mode in self.supportedGameModes:
            if mode == "normal":
                self.GameModes['Normal'] = (
                    "Play through the normal story with randomized gameplay."
                )
            elif mode == "katn":
                self.GameModes['Race - Kefka @ Narshe'] = (
                    "Race through the story and defeat Kefka at Narshe"
                )
            elif mode == "ancientcave":
                self.GameModes['Ancient Cave'] = (
                    "Play though a long randomized dungeon."
                )
            elif mode == "speedcave":
                self.GameModes['Speed Cave'] = (
                    "Play through a medium randomized dungeon."
                )
            elif mode == "racecave":
                self.GameModes['Race - Randomized Cave'] = (
                    "Race through a short randomized dungeon."
                )
            elif mode == "dragonhunt":
                self.GameModes['Race - Dragon Hunt'] = (
                    "Race to kill all 8 dragons."
                )

    def compileSupportedPresets(self):
        for mode in self.supportedPresets:
            if mode == "newplayer":
                self.GamePresets['New Player'] = (
                    "b c e g i m n o p q r s t w y z alasdraco "
                    "capslockoff partyparty makeover johnnydmad"
                )
            elif mode == "intermediateplayer":
                self.GamePresets['Intermediate Player'] = (
                    "b c d e g i j k l m n o p q r s t w y z alasdraco "
                    "capslockoff makeover partyparty johnnydmad notawaiter "
                    "mimetime"
                )
            elif mode == "advancedplayer":
                self.GamePresets['Advanced Player'] = (
                    "b c d e f g h i j k l m n o p q r s t u w y z alasdraco "
                    "capslockoff johnnydmad makeover notawaiter partyparty "
                    "dancingmaduin bsiab mimetime randombosses"
                )
            elif mode == "raceeasy":
                self.GamePresets['KaN Race - Easy'] = (
                    "b c d e f g i j k m n o p q r s t w y z capslockoff "
                    "johnnydmad makeover notawaiter partyparty madworld"
                )
            elif mode == "racemedium":
                self.GamePresets['KaN Race - Medium'] = (
                    "b c d e f g i j k m n o p q r s t u w y z capslockoff "
                    "johnnydmad makeover notawaiter partyparty "
                    "electricboogaloo randombosses madworld"
                )
            elif mode == "raceinsane":
                self.GamePresets['KaN Race - Insane'] = (
                    "b c d e f g i j k m n o p q r s t u w y z capslockoff "
                    "johnnydmad makeover notawaiter partyparty darkworld "
                    "madworld bsiab electricboogaloo randombosses"
                )

    # Get seed generation parameters from UI to prepare for 
    # seed generation. This will show a confirmation dialog, 
    # and call the local Randomizer.py file and pass arguments 
    # to it
    def generateSeed(self):

        self.romText = self.romInput.text()

        # Check to see if the supplied output directory exists.
        if os.path.isdir(self.romOutput.text()):
            # It does, use that directory.
            self.romOutputDirectory = self.romOutput.text()
        elif self.romOutput.text() == '':
            # It does not, but the text box is blank. Use the 
            # directory that the ROM file is in.
            self.romOutputDirectory = self.romOutput.placeholderText()
        else:
            # The supplied path is invalid. Raise an error.
            QMessageBox.about(
                self,
                "Error",
                "That output directory does not exist."
            )
            return

        if self.romText == "":
            QMessageBox.about(
                self,
                "Error",
                "You need to select a FFVI rom!"
            )
        else:
            if not os.path.exists(self.romText):
                self.romInput.setText('')
                QMessageBox.about(
                    self,
                    "Error",
                    "No ROM was found at the path "
                    + str(self.romText)
                    + ". Please choose a different ROM file."
                )
                return
            try:
                f = open(self.romText, 'rb')
                data = f.read()
                f.close()
                md5_hash = hashlib.md5(data).hexdigest()
                if md5_hash not in utils.WELL_KNOWN_ROM_HASHES:
                    confirm_hash = QMessageBox.question(
                        self,
                        "WARNING!",
                        "The md5 hash of this file does not match the known hashes of the english FF6 1.0 rom!"
                        + os.linesep
                        + "Continue Anyway?",
                        QMessageBox.Yes | QMessageBox.Cancel
                    ) == QMessageBox.Yes
                    if not confirm_hash:
                        return
            except IOError as e:
                QMessageBox.about(self, "Error", str(e))
                return

            self.seed = self.seedInput.text()

            displaySeed = self.seed

            flagMsg = ""

            if self.seed == "":
                displaySeed = "(none)"

            flagMode = ""
            for flag in self.flags:
                if len(flag) > 1:
                    flagMode += " " + flag
                else:
                    flagMode += flag

                flagMsg = ""
            flagMode = flagMode.strip()
            for flag in self.flags:
                if flagMsg != "":
                    flagMsg += "\n-"
                flagMsg += flag
            if flagMsg == "":
                QMessageBox.about(
                    self,
                    "Error",
                    "You need to select a flag and/or code!"
                )
                return

            if "bingoboingo" in self.flags:
                bingo = BingoPrompts()
                bingo.setModal(True)
                bingo.exec()

                bingotype = ""
                if bingo.abilities:
                    bingotype += "a"
                if bingo.items:
                    bingotype += "i"
                if bingo.monsters:
                    bingotype += "m"
                if bingo.spells:
                    bingotype += "s"

                if bingotype != "":
                    self.bingotype = bingotype
                else:
                    return
                self.bingodiff = bingo.difficulty
                self.bingosize = bingo.grid_size
                self.bingocards = bingo.num_cards

            # This makes the flag string more readable in 
            # the confirm dialog
            message = (f"Rom: {self.romText}\n"
                       f"Output: {self.romOutputDirectory}\n"
                       f"Seed: {displaySeed}\n"
                       f"Number of seeds: {self.seedCount.text()}\n"
                       f"Mode: {self.mode}\n"
                       f"Flags: \n-{flagMsg}\n"
                       f"(Hyphens are not actually used in seed generation)"
                       )
            continue_confirmed = QMessageBox.question(
                self,
                "Confirm Seed Generation?",
                message,
                QMessageBox.Yes | QMessageBox.Cancel
            ) == QMessageBox.Yes
            if continue_confirmed:
                self.clearConsole()
                self.seed = self.seed or int(time.time())
                seedsToGenerate = int(self.seedCount.text())
                resultFiles = []
                for currentSeed in range(seedsToGenerate):
                    print("Rolling seed " + str(currentSeed + 1) + " of " + str(seedsToGenerate) + ".")
                    # User selects confirm/accept/yes option
                    bundle = f"{self.version}|{self.mode}|{flagMode}|{self.seed}"
                    # remove spam if the Randomizer asks for input
                    # TODO: guify that stuff
                    # Hash check can be moved out to when you pick 
                    # the file. If you delete the file between picking 
                    # it and running, just spit out an error, no need 
                    # to prompt. 
                    # Randomboost could send a signal ask for a number 
                    # or whatever, but maybe it's better to just remove 
                    # it or pick a fixed number?
                    QtCore.pyqtRemoveInputHook()
                    # TODO: put this in a new thread
                    try:
                        kwargs = {
                            "sourcefile": self.romText,
                            "seed": bundle,
                            "output_directory": self.romOutputDirectory,
                            "bingotype": self.bingotype,
                            "bingosize": self.bingosize,
                            "bingodifficulty": self.bingodiff,
                            "bingocards": self.bingocards,
                            "from_gui": True,
                        }
                        # pool = multiprocessing.Pool()
                        pool = customthreadpool.NonDaemonPool(1)
                        x = pool.apply_async(func=randomize, kwds=kwargs)
                        x.get()
                        pool.close()
                        pool.join()
                        # generate the output file name since we're using subprocess now instead of a direct call
                        if '.' in self.romText:
                            tempname = os.path.basename(self.romText).rsplit('.', 1)
                        else:
                            tempname = [os.path.basename(self.romText), 'smc']
                        seed = bundle.split("|")[-1]
                        resultFile = os.path.join(self.romOutputDirectory,
                                                  '.'.join([os.path.basename(tempname[0]),
                                                            str(seed), tempname[1]]))
                        if self.seed:
                            self.seed = str(int(self.seed) + 1)
                    except Exception as e:
                        traceback.print_exc()
                        QMessageBox.critical(
                            self,
                            "Error creating ROM",
                            str(e),
                            QMessageBox.Ok
                        )
                    else:
                        resultFiles.append(resultFile)
                        if currentSeed + 1 == seedsToGenerate:
                            if seedsToGenerate == 1:
                                QMessageBox.information(
                                    self,
                                    "Successfully created ROM",
                                    "Result file\n------------\n" + f"{resultFile}",
                                    QMessageBox.Ok
                                )
                            elif seedsToGenerate > 10:
                                QMessageBox.information(
                                    self,
                                    f"Successfully created {seedsToGenerate} ROMs",
                                    f"{seedsToGenerate} ROMs have been created in {self.romOutputDirectory}.",
                                    QMessageBox.Ok
                                )
                            else:
                                resultFilesString = "\n------------\n".join(resultFiles)
                                QMessageBox.information(
                                    self,
                                    f"Successfully created {seedsToGenerate} ROMs",
                                    "Result files\n------------\n" + f"{resultFilesString}",
                                    QMessageBox.Ok
                                )
                        else:
                            self.clearConsole()

                    finally:
                        currentSeed += 1

    # Read each dictionary and update text field 
    # showing flag codes based upon
    # flags denoted as 'True'
    def updateFlagString(self):
        self.flagsChanging = True
        self.flagString.clear()
        temp = ""
        for x in range(0, len(self.flags)):
            flag = self.flags[x]
            temp += flag + " "
        self.flagString.setText(temp)
        self.flagsChanging = False

    # read through dictionaries and set flag checkboxes as 'checked'
    def updateFlagCheckboxes(self):
        for t, d in zip(self.tablist, self.dictionaries):
            # create a list of all checkbox objects from the 
            # current QTabWidget
            children = t.findChildren(FlagCheckBox)

            # enumerate checkbox objects and set them to 'checked' if
            # corresponding
            #   flag value is true
            for c in children:
                value = c.value
                # print(value + str(d[value]['checked']))
                if d[value]['checked']:
                    c.setProperty('checked', True)
                else:
                    c.setProperty('checked', False)

    def updateRomOutputPlaceholder(self, value):
        try:
            self.romOutput.setPlaceholderText(os.path.dirname(value))
        except ValueError:
            pass

    def clearConsole(self):
        os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == "__main__":
    multiprocessing.freeze_support()
    print(
        "Loading GUI, checking for config file, "
        "updater file and updates please wait."
    )
    try:
        if not update_needed():
            App = QApplication(sys.argv)
            window = Window()
            time.sleep(3)
            sys.exit(App.exec())
    except Exception:
        traceback.print_exc()
