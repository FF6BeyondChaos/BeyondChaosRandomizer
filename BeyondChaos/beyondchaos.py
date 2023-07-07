# Standard library imports
import configparser
import hashlib
import subprocess
import multiprocessing.process
import os
import sys
import time
import traceback
from hashlib import md5

# Related third-party imports
try:
    import requests.exceptions
    from PyQt5 import QtGui, QtCore
    from PyQt5.QtGui import QCursor
    from PyQt5.QtWidgets import (
            QPushButton, QCheckBox, QWidget, QVBoxLayout, QLabel, QGroupBox,
            QHBoxLayout, QLineEdit, QComboBox, QFileDialog, QApplication,
            QTabWidget, QInputDialog, QScrollArea, QMessageBox,
            QGraphicsDropShadowEffect, QGridLayout, QSpinBox, QDoubleSpinBox,
            QDialog, QDialogButtonBox, QMenu, QMainWindow, QDesktopWidget,
            QLayout, QFrame)
    from PIL import Image, ImageOps
except ImportError as e:
    print('ERROR: ' + str(e))
    import traceback

    traceback.print_exc()
    input('Press enter to quit.')
    exit(0)

# Local application imports
import utils
from multiprocessing import Process, Pipe
from config import (read_flags, write_flags, validate_files, are_updates_hidden, updates_hidden,
                    get_input_path, get_output_path, save_version, check_player_sprites, check_remonsterate)
from options import (NORMAL_FLAGS, MAKEOVER_MODIFIER_FLAGS, get_makeover_groups)
from update import (get_updater)
from randomizer import randomize, VERSION, BETA, MD5HASHNORMAL, MD5HASHTEXTLESS, MD5HASHTEXTLESS2

if sys.version_info[0] < 3:
    raise Exception("Python 3 or a more recent version is required. "
                    "Report this to https://github.com/FF6BeyondChaos/BeyondChaosRandomizer/issues")


# Extended QButton widget to hold flag value - NOT USED PRESENTLY
class FlagButton(QPushButton):
    def __init__(self, text, value):
        super(FlagButton, self).__init__()
        self.setText(text)
        self.value = value


class GenConfirmation(QDialog):
    def __init__(self, header, flag_list):
        super().__init__()
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        screen_size = QDesktopWidget().screenGeometry(-1)
        self.setMinimumSize(
            int(min(screen_size.width() / 2, 300)),
            int(screen_size.height() * .5)
        )
        self.left = int(screen_size.width() / 2 - self.width() / 2)
        self.top = int(screen_size.height() / 2 - self.height() / 2)
        self.setWindowTitle("Confirm Seed Generation?")

        grid_layout = QGridLayout()
        grid_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        header_text = QLabel(header)

        flag_list_label = QLabel(flag_list)
        flag_list_scroll = QScrollArea(self)
        flag_list_scroll.setWidgetResizable(True)
        flag_list_scroll.setWidget(flag_list_label)
        flag_list_scroll.setStyleSheet("margin-bottom: 10px;")

        grid_layout.addWidget(header_text, 1, 0, 1, 9)
        grid_layout.addWidget(flag_list_scroll, 2, 0, 1, 9)

        self.confirm_pushbutton = QPushButton("Confirm")
        grid_layout.addWidget(self.confirm_pushbutton, 3, 1, 1, 3)
        self.confirm_pushbutton.clicked.connect(self.button_pressed)

        self.cancel_pushbutton = QPushButton("Cancel")
        grid_layout.addWidget(self.cancel_pushbutton, 3, 5, 1, 3)
        self.cancel_pushbutton.clicked.connect(self.button_pressed)

        self.setLayout(grid_layout)

    def button_pressed(self):
        if self.sender() == self.cancel_pushbutton:
            self.reject()
        elif self.sender() == self.confirm_pushbutton:
            self.accept()


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


def update_bc(wait=False, suppress_prompt=False):
    try:
        # Tests internet connectivity. Throws a ConnectionError if offline.
        # We want to test connectivity here before firing up BeyondChaosUpdater.
        requests.head(url='http://www.google.com')
        run_updater = False
        if not suppress_prompt:
            update_prompt = QMessageBox()
            update_prompt.setWindowTitle("Beyond Chaos Updater")
            update_prompt.setText("Beyond Chaos will check for updates to the core randomizer, character sprites, and "
                                  "monster sprites. If updates are performed, BeyondChaos.exe will automatically close.")
            update_prompt.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
            update_prompt_button_clicked = update_prompt.exec()
            if update_prompt_button_clicked == QMessageBox.Ok:
                run_updater = True

        if run_updater or suppress_prompt:
            updates_hidden(False)
            print("Starting Beyond Chaos Updater...\n")
            args = ["-pid " + str(os.getpid())]
            os.system('cls' if os.name == 'nt' else 'clear')
            try:
                update_process = subprocess.Popen(args=args, executable="BeyondChaosUpdater.exe")
                if wait:
                    update_process.wait()
            except FileNotFoundError:
                get_updater()
                update_process = subprocess.Popen(args=args, executable="BeyondChaosUpdater.exe")
                if wait:
                    update_process.wait()

    except requests.exceptions.ConnectionError:
        update_bc_failure_message = QMessageBox()
        update_bc_failure_message.setIcon(QMessageBox.Warning)
        update_bc_failure_message.setWindowTitle("No Internet Connection")
        update_bc_failure_message.setText("You are currently offline. Please connect to the internet to perform "
                                          "updates to Beyond Chaos.")
        update_bc_failure_message.setStandardButtons(QMessageBox.Close)
        update_bc_failure_message.exec()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        # window geometry data
        self.title = "Beyond Chaos Randomizer " + VERSION
        screen_size = QDesktopWidget().screenGeometry(-1)
        self.width = int(min(screen_size.width() / 2, 1000))
        self.height = int(screen_size.height() * .8)
        self.left = int(screen_size.width() / 2 - self.width / 2)
        self.top = int(screen_size.height() / 2 - self.height / 2)

        # values to be sent to Randomizer
        self.romText = ""
        self.romOutputDirectory = ""
        self.version = "CE-5.0.2"
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
        self.makeover_groups = get_makeover_groups()
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
            "newplayer", "intermediateplayer", "advancedplayer", "chaoticplayer", "raceeasy",
            "racemedium", "raceinsane"
        ]
        # dictionary of game presets from drop down
        self.GamePresets = {}

        # tabs names for the tabs in flags box
        self.tabNames = [
            "Flags", "Sprites", "SpriteCategories", "Battle", "Aesthetic/Accessibility",
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
        self.initFlags()

        # create window using geometry data
        self.initWindow()

        self.romInput.setText(self.romText)
        self.romOutput.setText(self.romOutputDirectory)
        self.updateFlagString()
        # self.updateFlagCheckboxes()
        self.flagButtonClicked()
        self.updatePresetDropdown()
        self.clearUI()

    def initWindow(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # build the UI
        self.createLayout()

        previousRomPath = get_input_path()
        previousOutputDirectory = get_output_path()

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

        menu_separator = self.menuBar().addMenu("|")
        menu_separator.setEnabled(False)

        if not BETA and validation_result:
            self.menuBar().addAction("Update Available", update_bc)
        else:
            self.menuBar().addAction("Check for Updates", update_bc)

        # Primary Vertical Box Layout
        vbox = QVBoxLayout()

        title_label = QLabel("Beyond Chaos Randomizer")
        font = QtGui.QFont("Arial", 24, QtGui.QFont.Black)
        title_label.setFont(font)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setMargin(10)
        vbox.addWidget(title_label)

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

        self.labelRomError = QLabel()
        self.labelRomError.setStyleSheet("color: darkred;")
        self.labelRomError.setHidden(True)
        gridLayout.addWidget(self.labelRomError, 2, 2, 1, 3)

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
        gridLayout.addWidget(lblRomOutput, 3, 1)

        self.romOutput = QLineEdit()
        self.romInput.textChanged[str].connect(self.validateInputRom)
        gridLayout.addWidget(self.romOutput, 3, 2, 1, 3)

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
        gridLayout.addWidget(btnRomOutput, 3, 5)

        # SEED INPUT
        lblSeedInput = QLabel("Seed Number:")
        lblSeedInput.setAlignment(QtCore.Qt.AlignRight |
                                  QtCore.Qt.AlignVCenter)
        gridLayout.addWidget(lblSeedInput, 4, 1)

        self.seedInput = QLineEdit()
        self.seedInput.setPlaceholderText("Optional")
        gridLayout.addWidget(self.seedInput, 4, 2)

        lblSeedCount = QLabel("Number to Generate:")
        lblSeedCount.setAlignment(QtCore.Qt.AlignRight |
                                  QtCore.Qt.AlignVCenter)
        gridLayout.addWidget(lblSeedCount, 4, 3)

        self.seedCount = QSpinBox()
        self.seedCount.setValue(1)
        self.seedCount.setMinimum(1)
        self.seedCount.setMaximum(99)
        self.seedCount.setFixedWidth(40)
        gridLayout.addWidget(self.seedCount, 4, 4)

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
        gridLayout.addWidget(btnGenerate, 4, 5)

        groupLayout.setLayout(gridLayout)
        return groupLayout

    def GroupBoxTwoLayout(self):
        self.compileModes()
        self.compileSupportedPresets()
        mode_and_preset_group = QGroupBox()
        mode_and_preset_layout = QGridLayout()

        # ---- Game Mode Drop Down ---- #
        gameModeLabel = QLabel("Game Mode:")
        gameModeLabel.setStyleSheet("padding-left: 22px;")
        mode_and_preset_layout.addWidget(gameModeLabel, 1, 1)
        for item in self.GameModes.items():
            self.modeBox.addItem(item[0])
        self.modeBox.currentTextChanged.connect(
            lambda: self.updateGameDescription()
        )
        mode_and_preset_layout.addWidget(self.modeBox, 1, 2)

        # ---- Preset Flags Drop Down ---- #
        presetModeLabel = QLabel("Preset Flags:")
        presetModeLabel.setStyleSheet("padding-left: 22px;")
        mode_and_preset_layout.addWidget(presetModeLabel, 1, 3)
        self.presetBox.addItem("Select a flagset")
        self.loadSavedFlags()
        for item in self.GamePresets.items():
            self.presetBox.addItem(item[0])

        self.presetBox.currentTextChanged.connect(
            lambda: self.updatePresetDropdown()
        )
        mode_and_preset_layout.addWidget(self.presetBox, 1, 4)

        flagDescriptionLabel = QLabel("Preset Description:")
        flagDescriptionLabel.setStyleSheet(
            "font-size:14px;"
            "height:24px;"
            "color:#253340;"
            "padding-left: 22px;"
        )
        mode_and_preset_layout.addWidget(flagDescriptionLabel,1, 5)

        self.flagDescription.setStyleSheet(
            "font-size:14px;"
            "height:24px;"
            "color:#253340;"
        )
        mode_and_preset_layout.addWidget(self.flagDescription, 1, 6)

        mode_and_preset_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        mode_and_preset_group.setLayout(mode_and_preset_layout)
        mode_and_preset_group.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        return mode_and_preset_group

    def flagBoxLayout(self):
        groupBoxTwo = QGroupBox()
        middleHBox = QHBoxLayout()
        middleRightGroupBox = QGroupBox("Flag Selection")
        tabVBoxLayout = QVBoxLayout()
        tabs = QTabWidget()
        control_fixed_width = 70
        control_fixed_height = 20

        # loop to add tab objects to 'tabs' TabWidget
        for t, d, names in zip(self.tablist,
                               self.dictionaries,
                               self.tabNames):
            tabObj = QScrollArea()
            tabs.addTab(tabObj, names)
            tablayout = QGridLayout()
            tablayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
            flagcount = 0
            currentRow = 0
            for flagname, flag in d.items():
                if flag['object'].inputtype == 'boolean':
                    # cbox = FlagCheckBox("", flagname)
                    cbox = QPushButton("No")
                    cbox.flag = flag['object']
                    if (flagname == "remonsterate" and not len(check_remonsterate()) == 0) or\
                       (flagname == "makeover" and not len(check_player_sprites()) == 0):
                        cbox.setEnabled(False)
                    self.checkBoxes.append(cbox)
                    cbox.setFixedWidth(control_fixed_width)
                    cbox.setFixedHeight(control_fixed_height)
                    cbox.setCheckable(True)
                    cbox.value = flagname

                    flaglbl = QLabel(f"{flagname}")
                    flagdesc = QLabel(f"{flag['object'].long_description}")

                    tablayout.addWidget(cbox, currentRow, 1)
                    tablayout.addWidget(flaglbl, currentRow, 2)
                    tablayout.addWidget(flagdesc, currentRow, 4)
                    cbox.clicked.connect(lambda checked:
                                         self.flagButtonClicked()
                                         )
                    flagcount += 1
                elif flag['object'].inputtype == 'float2':
                    nbox = QDoubleSpinBox()
                    nbox.flag = flag['object']
                    nbox.setMinimum(0)
                    nbox.setSingleStep(.1)
                    nbox.default = 1.00
                    nbox.setSuffix("x")
                    nbox.setValue(nbox.default)
                    nbox.text = flagname
                    nbox.setFixedWidth(control_fixed_width)
                    nbox.setFixedHeight(control_fixed_height)

                    flaglbl = QLabel(f"{flagname}")
                    flagdesc = QLabel(f"{flag['object'].long_description}")

                    tablayout.addWidget(nbox, currentRow, 1)
                    tablayout.addWidget(flaglbl, currentRow, 2)
                    tablayout.addWidget(flagdesc, currentRow, 4)
                    nbox.valueChanged.connect(lambda: self.flagButtonClicked())
                    flagcount += 1
                elif flag['object'].inputtype == 'integer':
                    nbox = QSpinBox()
                    nbox.flag = flag['object']
                    nbox.default = int(flag['object'].default_value)
                    nbox.setMinimum(int(flag['object'].minimum_value))
                    nbox.setMaximum(int(flag['object'].maximum_value))
                    nbox.setFixedWidth(control_fixed_width)
                    nbox.setFixedHeight(control_fixed_height)
                    if flagname == "cursepower":
                        nbox.setSpecialValueText("Random")
                    else:
                        nbox.setSpecialValueText("Off")
                    nbox.setValue(nbox.default)
                    nbox.text = flagname

                    flaglbl = QLabel(f"{flagname}")
                    flagdesc = QLabel(f"{flag['object'].long_description}")

                    tablayout.addWidget(nbox, currentRow, 1)
                    tablayout.addWidget(flaglbl, currentRow, 2)
                    tablayout.addWidget(flagdesc, currentRow, 4)
                    nbox.valueChanged.connect(lambda: self.flagButtonClicked())
                    flagcount += 1
                elif flag['object'].inputtype == 'combobox':
                    cmbbox = QComboBox()
                    cmbbox.flag = flag['object']
                    cmbbox.addItems(flag['object'].choices)
                    cmbbox.text = flagname
                    cmbbox.setFixedWidth(control_fixed_width)
                    cmbbox.setFixedHeight(control_fixed_height)
                    cmbbox.setCurrentIndex(flag['object'].default_index)
                    if self.makeover_groups and flagname in self.makeover_groups:
                        flaglbl = QLabel(f"{flagname} (" + str(self.makeover_groups[flagname]) +
                                         ")")
                        flagdesc = QLabel(f"{flag['object'].long_description}")
                    else:
                        flaglbl = QLabel(f"{flagname}")
                        flagdesc = QLabel(f"{flag['object'].long_description}")
                    tablayout.addWidget(cmbbox, currentRow, 1)
                    tablayout.addWidget(flaglbl, currentRow, 2)
                    tablayout.addWidget(flagdesc, currentRow, 4)
                    cmbbox.activated[str].connect(lambda: self.flagButtonClicked())
                    flagcount += 1
                currentRow += 1

            v_spacer = QFrame()
            v_spacer.setFrameShape(QFrame.VLine)
            v_spacer.setFrameShadow(QFrame.Sunken)
            v_spacer.setFixedWidth(5)
            v_spacer.setStyleSheet("margin: 5px 0 5px 0;")
            tablayout.addWidget(v_spacer, 0, 3, flagcount, 1)

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
            if child.isEnabled():
                for v in values:
                    v = str(v).lower()
                    if type(child) == QPushButton and v == child.value:
                        child.setChecked(True)
                        child.setText("Yes")
                        self.flags.append(v)
                    elif type(child) in [QSpinBox] and str(v).startswith(child.text.lower()):
                        if ":" in v:
                            try:
                                child.setValue(int(str(v).split(":")[1]))
                                self.flags.append(v)
                            except ValueError:
                                if str(v).split(":")[1] == child.specialValueText().lower():
                                    child.setValue(child.minimum())
                                    self.flags.append(v)
                    elif type(child) in [QDoubleSpinBox] and str(v).startswith(child.text.lower()):
                        if ":" in v:
                            try:
                                value = float(str(v).split(":")[1])
                                if value >= 0:
                                    child.setValue(value)
                                    self.flags.append(v)
                            except ValueError:
                                pass
                    elif type(child) in [QComboBox] and str(v).startswith(child.text.lower()):
                        if ":" in v:
                            index_of_value = child.findText(str(v).split(":")[1], QtCore.Qt.MatchFixedString)
                            child.setCurrentIndex(index_of_value)
                            self.flags.append(v)
        self.updateFlagString()
        self.flagsChanging = False

    # (At startup) Opens reads code flags/descriptions and
    #   puts data into separate dictionaries
    def initFlags(self):
        for flag in sorted(NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS, key=lambda x: x.name):
            if flag.category == "flags":
                d = self.flag
            elif flag.category == "aesthetic":
                d = self.aesthetic
            elif flag.category == "sprite":
                d = self.sprite
            elif flag.category == "spriteCategories":
                d = self.spriteCategories
            elif flag.category == "experimental":
                d = self.experimental
            elif flag.category == "gamebreaking":
                d = self.gamebreaking
            elif flag.category == "field":
                d = self.field
            elif flag.category == "characters":
                d = self.characters
            elif flag.category == "beta":
                d = self.beta
            elif flag.category == "battle":
                d = self.battle
            else:
                print(f"Flag {flag.name} does not have a valid category.")
                continue

            d[flag.name] = {
                'checked': False,
                'object': flag
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
            write_flags(
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
        flagset = read_flags()
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
                "Flags designed for a chaotic player"
            )
            self.flagString.setText(flags)
            self.mode = "normal"
            self.modeBox.setCurrentIndex(0)
        elif index == 5:
            self.flagDescription.setText(
                "Flags designed for KaN easy difficulty races"
            )
            self.flagString.setText(flags)
            self.mode = "katn"
            self.modeBox.setCurrentIndex(1)
        elif index == 6:
            self.flagDescription.setText(
                "Flags designed for KaN medium difficulty races"
            )
            self.flagString.setText(flags)
            self.mode = "katn"
            self.modeBox.setCurrentIndex(1)
        elif index == 7:
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
        self.initFlags()
        self.clear_controls()
        self.flagString.clear()
        self.flags.clear()
        self.updateGameDescription()

    def clear_controls(self):
        for tab in self.tablist:
            for child in tab.children():
                if type(child) == QPushButton:
                    child.setChecked(False)
                    child.setText("No")
                elif type(child) == QSpinBox or type(child) == QDoubleSpinBox:
                    child.setValue(child.default)
                elif type(child) == QComboBox:
                    child.setCurrentIndex(child.flag.default_index)

    # When flag UI button is checked, update corresponding
    # dictionary values
    def flagButtonClicked(self):
        # Check self.flagsChanging first. If that is set, a new flag preset has been selected, which is causing
        #  the controls to change and call this method. But we do not want to do anything then, otherwise it can
        #  add duplicate entries to the flag string
        if not self.flagsChanging:
            self.flags.clear()
            for t, d in zip(self.tablist, self.dictionaries):
                children = t.findChildren(QPushButton)
                for c in children:
                    if c.isChecked():
                        c.setText("Yes")
                        d[c.value]['checked'] = True
                        self.flags.append(c.value)
                    else:
                        c.setText("No")
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
                    if c.currentIndex() != c.flag.default_index:
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
                    "b c e f g i n o p q r s t w y z makeover partyparty dancelessons lessfanatical "
                    "expboost:2.0 gpboost:2.0 mpboost:2.0 swdtechspeed:faster alasdraco capslockoff "
                    "johnnydmad questionablecontent relicmyhat"
                )
            elif mode == "intermediateplayer":
                self.GamePresets['Intermediate Player'] = (
                    "b c d e f g i j k m n o p q r s t u w y z makeover partyparty dancelessons electricboogaloo "
                    "swdtechspeed:faster alasdraco capslockoff johnnydmad notawaiter remonsterate relicmyhat"
                )
            elif mode == "advancedplayer":
                self.GamePresets['Advanced Player'] = (
                    "b c d e f g h i j k m n o p q r s t u w y z makeover partyparty dancelessons electricboogaloo "
                    "randombosses dancingmaduin:1 swdtechspeed:random alasdraco capslockoff johnnydmad notawaiter "
                    "remonsterate bsiab mimetime morefanatical questionablecontent relicmyhat"
                )
            elif mode == "chaoticplayer":
                self.GamePresets['Chaotic Player'] = (
                    "b c d e f g h i j k m n o p q r s t u w y z makeover partyparty dancelessons electricboogaloo "
                    "masseffect randombosses dancingmaduin:chaos swdtechspeed:random alasdraco capslockoff "
                    "johnnyachaotic notawaiter remonsterate bsiab mimetime questionablecontent randomboost:2 "
                    "allcombos supernatural mementomori:random thescenarionottaken relicmyhat"
                )
            elif mode == "raceeasy":
                self.GamePresets['KaN Race - Easy'] = (
                    "b c d e f g i j k m n o p q r s t w y z capslockoff "
                    "johnnydmad makeover notawaiter partyparty madworld relicmyhat"
                )
            elif mode == "racemedium":
                self.GamePresets['KaN Race - Medium'] = (
                    "b c d e f g i j k m n o p q r s t u w y z capslockoff "
                    "johnnydmad makeover notawaiter partyparty "
                    "electricboogaloo randombosses madworld relicmyhat"
                )
            elif mode == "raceinsane":
                self.GamePresets['KaN Race - Insane'] = (
                    "b c d e f g i j k m n o p q r s t u w y z capslockoff "
                    "johnnydmad makeover notawaiter partyparty darkworld "
                    "madworld bsiab electricboogaloo randombosses relicmyhat"
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
                flagMode += " " + flag

                flagMsg = ""
            flagMode = flagMode.strip()
            for flag in self.flags:
                if flagMsg:
                    if len(flag) == 1:
                        flagMsg += " "
                    else:
                        flagMsg += "\n"
                flagMsg += flag
            if flagMsg == "":
                QMessageBox.about(
                    self,
                    "Error",
                    "You need to select a flag!"
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
            message = (
                "{0: <10} {1}\n"
                "{2: <9} {3}\n"
                "{4: <10} {5}\n"
                "{6: <10} {7}\n"
                "{8: <10} {9}\n"
                "{10: <10}".format(
                    "Rom:", self.romText,
                    "Output:", self.romOutputDirectory,
                    "Seed:", displaySeed,
                    "Batch:", self.seedCount.text(),
                    "Mode:", self.mode,
                    "Flags:")
            )
            continue_confirmed = GenConfirmation(
                message,
                f"{flagMsg}"
            ).exec()
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
                            "infile_rom_path": self.romText,
                            "outfile_rom_path": self.romOutputDirectory,
                            "seed": bundle,
                            "bingotype": self.bingotype,
                            "bingosize": self.bingosize,
                            "bingodifficulty": self.bingodiff,
                            "bingocards": self.bingocards,
                            "application": "gui"
                        }
                        parent_connection, child_connection = Pipe()
                        randomize_process = Process(
                            target=randomize,
                            args=(child_connection,),
                            kwargs=kwargs
                        )
                        randomize_process.start()
                        while True:
                            if not randomize_process.is_alive():
                                raise RuntimeError("Unexpected error: The randomize child process died.")
                            if parent_connection.poll(timeout=5):
                                item = parent_connection.recv()
                            else:
                                item = None
                            if item:
                                try:
                                    if isinstance(item, str):
                                        print(item)
                                    elif isinstance(item, Exception):
                                        raise item
                                    elif isinstance(item, bool):
                                        break
                                except EOFError:
                                    break

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
                        randomize_error_message = QMessageBox()
                        randomize_error_message.setIcon(QMessageBox.Critical)
                        randomize_error_message.setWindowTitle("Exception: " + str(type(e).__name__))
                        randomize_error_message.setText("A " + str(type(e).__name__) + " exception occurred "
                                                        "that prevented randomization: " +
                                                        "<br>" +
                                                        str(e) +
                                                        "<br>" +
                                                        "<br>" +
                                                        "<b><u>Error Traceback for the Devs</u></b>:" +
                                                        "<br>" +
                                                        "<br>".join(traceback.format_exc().splitlines()))
                        randomize_error_message.setStandardButtons(QMessageBox.Close)
                        rem_button_clicked = randomize_error_message.exec()
                        if rem_button_clicked == QMessageBox.Close:
                            randomize_error_message.close()
                        traceback.print_exc()
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
    # def updateFlagCheckboxes(self):
    #     for t, d in zip(self.tablist, self.dictionaries):
    #         # create a list of all checkbox objects from the
    #         # current QTabWidget
    #         children = t.findChildren(FlagCheckBox)
    #
    #         # enumerate checkbox objects and set them to 'checked' if
    #         # corresponding
    #         #   flag value is true
    #         for c in children:
    #             value = c.value
    #             if d[value]['checked']:
    #                 c.setProperty('checked', True)
    #             else:
    #                 c.setProperty('checked', False)


    def validateInputRom(self, value):
        try:
            if not value == "":
                try:
                    with open(value, 'rb') as rom_file:
                        rom_hash = md5(rom_file.read()).hexdigest()
                    if rom_hash in [MD5HASHNORMAL, MD5HASHTEXTLESS, MD5HASHTEXTLESS2]:
                        self.labelRomError.setHidden(True)
                    else:
                        self.labelRomError.setText("WARNING! The selected file does not match supported "
                                                   "English FF3/FF6 v1.0 ROM files!")
                        self.labelRomError.setHidden(False)
                except FileNotFoundError:
                    self.romInput.setText("")
                    self.romInput.setPlaceholderText("")
                    self.labelRomError.setText("The previously used ROM file could not be found. Please select a "
                                               "new FF6 ROM file.")
                    self.labelRomError.setHidden(False)

            self.romOutput.setPlaceholderText(os.path.dirname(os.path.normpath(value)))
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
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    App = QApplication(sys.argv)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    try:
        if not BETA:
            required_update = False
            validation_result = []
            try:
                validation_result, required_update = validate_files()
                first_time_setup = False
                if required_update and 'config.ini' in validation_result:
                    first_time_setup = True
                if required_update or (validation_result and not are_updates_hidden()):
                    update_message = QMessageBox()
                    if first_time_setup:
                        update_message.setIcon(QMessageBox.Information)
                        update_message.setWindowTitle("First Time Setup")
                        update_message.setText("<b>Welcome to Beyond Chaos Community Edition!</b>" +
                                               "<br>" +
                                               "<br>" +
                                               "As part of first time setup, "
                                               "we need to download some required files and folders."
                                               "<br>" +
                                               "<br>" +
                                               "Press OK to launch the updater to download the required files."
                                               "<br>" +
                                               "Press Close to exit the program.")
                    elif required_update:
                        update_message.setIcon(QMessageBox.Warning)
                        update_message.setWindowTitle("Missing Required Files")
                        update_message.setText("Files that are required for the randomizer to function properly are missing "
                                               "from the randomizer directory:" +
                                               "<br>" +
                                               "<br>" +
                                               str(validation_result) +
                                               "<br>" +
                                               "<br>" +
                                               "Press OK to launch the updater to download the required files." +
                                               "<br>" +
                                               "Press Close to exit the program.")
                    else:
                        update_message.setIcon(QMessageBox.Question)
                        update_message.setWindowTitle("Update Available")
                        update_message.setText("Updates to Beyond Chaos are available!" +
                                               "<br>" +
                                               "<br>" +
                                               str(validation_result) +
                                               "<br>" +
                                               "<br>" +
                                               "Press OK to launch the updater or Close to skip updating. This pop-up will "
                                               "only show once per update.")

                    update_message.setStandardButtons(QMessageBox.Close | QMessageBox.Ok)
                    button_clicked = update_message.exec()
                    if button_clicked == QMessageBox.Close:
                        # Update_message informs the user about the update button on the UI.
                        update_message.close()
                        if required_update:
                            sys.exit()
                        else:
                            update_dismiss_message = QMessageBox()
                            update_dismiss_message.setIcon(QMessageBox.Information)
                            update_dismiss_message.setWindowTitle("Information")
                            update_dismiss_message.setText("The update will be available using the Update button on the "
                                                           "randomizer's menu bar.")
                            update_dismiss_message.setStandardButtons(QMessageBox.Close)
                            button_clicked = update_dismiss_message.exec()
                            if button_clicked == QMessageBox.Close:
                                update_dismiss_message.close()
                                updates_hidden(True)
                    elif button_clicked == QMessageBox.Ok:
                        if required_update and not first_time_setup:
                            save_version('core', '0.0')
                        elif first_time_setup:
                            save_version('core', VERSION)
                        if required_update:
                            # Test internet connectivity. Throws a ConnectionError if offline
                            requests.head(url='http://www.google.com')
                        update_bc(wait=True, suppress_prompt=True)
            except requests.exceptions.ConnectionError:
                if required_update:
                    failure_message = QMessageBox()
                    failure_message.setIcon(QMessageBox.Warning)
                    failure_message.setWindowTitle("No Internet Connection")
                    failure_message.setText("Beyond Chaos was unable to perform the required update because " +
                                            "no internet connection was available." +
                                            "<br><br>" +
                                            "Please connect to the internet and then try again.")
                    failure_message.setStandardButtons(QMessageBox.Close)
                    failure_message.exec()
                    sys.exit()
                else:
                    print("You are currently offline. Skipping the update check.")
                pass
        window = Window()
        time.sleep(3)
        sys.exit(App.exec())
    except Exception as e:
        error_message = QMessageBox()
        error_message.setIcon(QMessageBox.Critical)
        error_message.setWindowTitle("Exception: " + str(type(e).__name__))
        error_message.setText("A fatal " + str(type(e).__name__) + " exception occurred: " +
                              str(e) +
                              "<br>" +
                              "<br>" +
                              "<br>" +
                              "<br>" +
                              "<b><u>Error Traceback for the Devs</u></b>:" +
                              "<br>" +
                              "<br>" +
                              "<br>".join(traceback.format_exc().splitlines()))
        error_message.setStandardButtons(QMessageBox.Close)
        button_clicked = error_message.exec()
        if button_clicked == QMessageBox.Close:
            error_message.close()
        traceback.print_exc()
