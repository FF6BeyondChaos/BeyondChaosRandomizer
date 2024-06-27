# Standard library imports
import hashlib
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
    from PyQt5.QtGui import QCursor, QPalette, QColor, QColorConstants
    from PyQt5.QtWidgets import (
        QPushButton, QCheckBox, QWidget, QVBoxLayout, QLabel, QGroupBox,
        QHBoxLayout, QLineEdit, QComboBox, QFileDialog, QApplication,
        QTabWidget, QInputDialog, QScrollArea, QMessageBox,
        QGraphicsDropShadowEffect, QGridLayout, QSpinBox, QDoubleSpinBox,
        QDialog, QDialogButtonBox, QMenu, QMainWindow, QDesktopWidget,
        QLayout, QFrame, QStyle, QTextEdit, QSizePolicy, QSpacerItem)
    from PIL import Image, ImageOps
except ImportError as e:
    print('ERROR: ' + str(e))

    traceback.print_exc()
    input('Press enter to quit.')
    exit(0)

# Local application imports
import utils
import update
from multiprocessing import Process, Pipe
from config import (read_flags, write_flags, set_config_value, check_ini, check_player_sprites,
                    check_remonsterate, VERSION, BETA, MD5HASHNORMAL, MD5HASHTEXTLESS,
                    MD5HASHTEXTLESS2, SUPPORTED_PRESETS, config)
from options import (NORMAL_FLAGS, MAKEOVER_MODIFIER_FLAGS, get_makeover_groups, Options_, Flag)
from randomizer import randomize

if sys.version_info[0] < 3:
    raise Exception('Python 3 or a more recent version is required. '
                    'Report this to https://github.com/FF6BeyondChaos/BeyondChaosRandomizer/issues')

control_fixed_width = 70
control_fixed_height = 20
spacer_fixed_height = 5


class QDialogScroll(QDialog):
    def __init__(self, title: str = '', header: str = '', scroll_contents: QWidget = None,
                 left_button: str = '', right_button: str = '', icon=None):
        super().__init__()
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        screen_size = QDesktopWidget().screenGeometry(-1)
        self.setMinimumSize(
            int(min(screen_size.width() * .5, 500)),
            int(screen_size.height() * .5)
        )
        self.left = int(screen_size.width() / 2 - self.width() / 2)
        self.top = int(screen_size.height() / 2 - self.height() / 2)
        self.setWindowTitle(title)

        grid_layout = QGridLayout()
        grid_layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)

        header_text = QLabel(header)
        header_text.setOpenExternalLinks(True)

        flag_list_label = scroll_contents
        flag_list_scroll = QScrollArea(self)
        flag_list_scroll.setMinimumWidth(self.minimumWidth() - 100)
        flag_list_scroll.setEnabled(True)
        flag_list_scroll.setWidgetResizable(True)
        flag_list_scroll.setWidget(flag_list_label)

        grid_layout.addWidget(header_text, 1, 0, 1, 9)
        grid_layout.addWidget(flag_list_scroll, 2, 0, 1, 9)

        self.left_pushbutton = None
        self.right_pushbutton = None

        if left_button:
            self.left_pushbutton = QPushButton(left_button)
            grid_layout.addWidget(self.left_pushbutton, 3, 1, 1, 3)
            self.left_pushbutton.clicked.connect(self.button_pressed)

        if right_button:
            self.right_pushbutton = QPushButton(right_button)
            grid_layout.addWidget(self.right_pushbutton, 3, 5, 1, 3)
            self.right_pushbutton.clicked.connect(self.button_pressed)

        if icon:
            self.setWindowIcon(self.style().standardIcon(icon))

        self.setLayout(grid_layout)

    def button_pressed(self):
        try:
            if self.sender() == self.left_pushbutton:
                self.reject()
            elif self.sender() == self.right_pushbutton:
                self.accept()
        except Exception:
            pass


class BingoPrompts(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('WELCOME TO BEYOND CHAOS BINGO MODE')
        self.setMinimumWidth(600)
        self.abilities = False
        self.monsters = False
        self.items = False
        self.spells = False
        self.abilities_box = QCheckBox('Abilities', self)
        self.abilities_box.stateChanged.connect(self._toggle_abilities)
        self.monsters_box = QCheckBox('Monsters', self)
        self.monsters_box.stateChanged.connect(self._toggle_monsters)
        self.items_box = QCheckBox('Items', self)
        self.items_box.stateChanged.connect(self._toggle_items)
        self.spells_box = QCheckBox('Spells', self)
        self.spells_box.stateChanged.connect(self._toggle_spells)

        boxes_label = QLabel('Include what type of squares?', self)
        layout = QGridLayout(self)
        layout.addWidget(boxes_label)
        layout.addWidget(self.abilities_box)
        layout.addWidget(self.monsters_box)
        layout.addWidget(self.items_box)
        layout.addWidget(self.spells_box)

        self.grid_size = 5
        grid_size_label = QLabel('What size grid? (2-7)')
        self.grid_size_box = QSpinBox()
        self.grid_size_box.setRange(2, 7)
        self.grid_size_box.setValue(self.grid_size)
        self.grid_size_box.valueChanged.connect(self._set_grid_size)
        layout.addWidget(grid_size_label)
        layout.addWidget(self.grid_size_box)

        self.difficulty = 'n'
        difficulty_label = QLabel('What difficulty level?')
        self.difficulty_dropdown = QComboBox(self)
        for difficulty in ['Easy', 'Normal', 'Hard']:
            self.difficulty_dropdown.addItem(difficulty)
        self.difficulty_dropdown.setCurrentIndex(1)  # Normal
        self.difficulty_dropdown.currentTextChanged.connect(self._set_difficulty)
        layout.addWidget(difficulty_label)
        layout.addWidget(self.difficulty_dropdown)

        self.num_cards = 1
        num_cards_label = QLabel('Generate how many cards?')
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


def update_bc(suppress_prompt=False, force_download=False):
    if update.internet_connectivity_available():
        # Tests internet connectivity. Throws a ConnectionError if offline.
        # We want to test connectivity here before firing up BeyondChaosUpdater.
        run_updater = False
        if not suppress_prompt:
            update_prompt = QMessageBox()
            update_prompt.setIcon(QMessageBox.Information)
            update_prompt.setWindowTitle('Beyond Chaos Updater')
            update_prompt.setText(
                'The Beyond Chaos update process checks for the following:'
                '<ul><li>Updates to the core randomization files.</li>'
                '<li>Missing custom folder items required for randomization to function.</li>'
                '<li>New character sprites and monster sprites.</li></ul> '
                'Click OK to continue.'
            )
            update_prompt.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
            update_prompt_button_clicked = update_prompt.exec()
            if update_prompt_button_clicked == QMessageBox.Ok:
                run_updater = True

        if run_updater or suppress_prompt:
            set_config_value('Settings', 'updates_hidden', str(False))
            os.system('cls' if os.name == 'nt' else 'clear')
            update.run_updates(force_download=force_download, calling_program=App)

    else:
        update_bc_failure_message = QMessageBox()
        update_bc_failure_message.setWindowTitle('No Internet Connection')
        update_bc_failure_message.setStandardButtons(QMessageBox.Close)
        if force_download:
            update_bc_failure_message.setIcon(QMessageBox.Critical)
            update_bc_failure_message.setText('You are currently offline. Please connect to the internet and then run '
                                              'the program again to download the required Beyond Chaos '
                                              'randomization files.<br><br>'
                                              'Press close to exit the program.')
            response = update_bc_failure_message.exec()
            if response == QMessageBox.Close:
                sys.exit()
        else:
            update_bc_failure_message.setIcon(QMessageBox.Warning)
            update_bc_failure_message.setText('You are currently offline. '
                                              'Please connect to the internet to perform updates to Beyond Chaos.')
            update_bc_failure_message.exec()


def set_palette(style=None):
    if not style:
        style = config.get('Settings', 'gui_theme', fallback='Light')

    if style == 'Light':
        light_palette = QPalette()
        QApplication.setPalette(light_palette)
    elif style == 'Dark':
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, QColorConstants.White)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, QColorConstants.White)
        dark_palette.setColor(QPalette.Text, QColorConstants.White)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColorConstants.White)
        dark_palette.setColor(QPalette.BrightText, QColorConstants.Red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColorConstants.DarkGray)
        dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColorConstants.DarkGray)
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColorConstants.DarkGray)
        dark_palette.setColor(QPalette.Disabled, QPalette.Light, QColor(53, 53, 53))
        QApplication.setPalette(dark_palette)
    else:
        raise ValueError('Set Palette function received an unrecognized style: "' + str(style) + '".')

    set_config_value('Settings', 'gui_theme', style)


def toggle_palette():
    if config.get('Settings', 'gui_theme', fallback='Light') == 'Light':
        set_palette('Dark')
    else:
        set_palette('Light')


def handle_conflicts_and_requirements(conflicts: dict, requirements: dict):
    """
    Whenever a flag is activated, its list of conflicting flags is included to Window.conflicts.
    Whenever a flag is missing a requirement, it is included in Window.requirements.

    For every available flag, if that flag either conflicts with an active flag or is missing required flags to
        enable it, the flag needs to be both deactivated and its controls disabled to prevent activation.

    If the flag is not in either dictionary, the controls are enabled and the flag can be activated.

    Parameters:
        conflicts: A dictionary of all existing conflicts for all active flags.
        requirements: A dictionary of all flags currently missing their requirements.

    Returns:
        None
    """
    for flag in NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS:
        error_text = ''
        if conflicts and flag.name in conflicts.keys():
            if not error_text:
                error_text = ('<div style="color: red;">Flag disabled because:<ul style="margin: 0;"><li>' +
                              'It conflicts with the following '
                              + 'active flags: "' + '" and "'.join(conflicts[flag.name]) + '"</li>')
        if requirements and flag.name in requirements.keys() and requirements[flag.name]:
            if not error_text:
                error_text = ('<div style="color: red;">Flag disabled because:<ul style="margin: 0;"><li>     ' +
                              requirements[flag.name] + '</li>')
            else:
                error_text += '<li>' + requirements[flag.name] + '</li>'

        if error_text:
            # Set controls to default value (turn off flag)
            flag_control = flag.controls[0]
            flag_control.setStyleSheet('background-color: white; border: none;')
            if flag.input_type in ['float2', 'integer']:
                flag_control.setValue(flag_control.default)
            elif flag.input_type == 'combobox':
                flag_control.setCurrentIndex(flag.default_index)
            else:
                flag_control.setText('No')
                flag_control.setChecked(False)
            flag_control.setDisabled(True)
            flag.controls[2].setText(error_text + '</ul></div>' + flag.long_description)
        else:
            # Enable control
            flag.controls[0].setDisabled(False)
            flag.controls[2].setText(flag.long_description)


def handle_children(flag, parent_value):
    """
    For a parent flag with a specified value, check to see if the flag has any children. The children are contained in
        a dict object containing the child's name and the value the parent should be set to for the child to be
        visible.

    For each child where the parent is the correct value to make it visible, make the child visible.

    For each child where the parent is NOT the correct value to make it visible, turn the flag off by
        setting it to its default value in addition to making the child invisible.

    Returns:
        None
    """
    for flag_name, required_parent_value in flag.children.items():
        if parent_value == required_parent_value:
            flag_object = Options_.get_flag(flag_name)
            for control in flag_object.controls:
                # Make all controls visible
                control.setVisible(True)

            for spacer in flag_object.margins:
                spacer.changeSize(0, spacer_fixed_height)
        else:
            # Set controls to default value (turn off flag)
            flag_object = Options_.get_flag(flag_name)
            flag_control = flag_object.controls[0]
            if flag_object.input_type in ['float2', 'integer']:
                flag_control.setValue(flag_control.default)
            elif flag_object.input_type == 'combobox':
                flag_control.setCurrentIndex(flag_object.default_index)
            else:
                flag_control.setChecked(False)

            # Make all controls invisible
            for control in flag_object.controls:
                control.setVisible(False)

            for spacer in flag_object.margins:
                spacer.changeSize(0, 0)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        # window geometry data
        self.title = 'Beyond Chaos Randomizer ' + VERSION
        screen_size = QDesktopWidget().screenGeometry(-1)
        self.width = int(min(screen_size.width() / 2, 1000))
        self.height = int(screen_size.height() * .8)
        self.left = int(screen_size.width() / 2 - self.width / 2)
        self.top = int(screen_size.height() / 2 - self.height / 2)

        # values to be sent to Randomizer
        self.romText = ''
        self.romOutputDirectory = ''
        self.version = 'CE-6.0.2'
        self.mode = 'normal'
        self.seed = ''
        self.flags = []
        self.bingo_type = []
        self.bingo_size = 5
        self.bingo_diff = ''
        self.bingo_cards = 1

        # dictionaries to hold flag data
        self.aesthetic = {}
        self.sprite = {}
        self.sprite_categories = {}
        self.experimental = {}
        self.gamebreaking = {}
        self.field = {}
        self.characters = {}
        self.flag = {}
        self.battle = {}
        self.beta = {}
        self.quality_of_life = {}
        self.dictionaries = [
            self.flag, self.quality_of_life, self.sprite, self.sprite_categories, self.aesthetic, self.battle,
            self.field, self.characters, self.experimental, self.gamebreaking,
            self.beta
        ]
        self.makeover_groups = get_makeover_groups()
        # keep a list of all checkboxes
        self.check_boxes = []
        self.conflicts = {}
        self.requirements = {}

        # array of supported game modes
        self.supported_game_modes = [
            'normal', 'katn', 'ancientcave', 'speedcave', 'racecave',
            'dragonhunt'
        ]
        # dictionary of game modes for drop down
        self.game_modes = {}

        # dictionary of game presets from drop down
        self.game_presets = SUPPORTED_PRESETS

        # tabs names for the tabs in flags box
        self.tab_names = [
            'Core', 'Quality of Life', 'Sprites', 'SpriteCategories', 'Aesthetic', 'Battle',
            'Field', 'Characters', 'Experimental', 'Gamebreaking', 'Beta'
        ]

        # ui elements
        self.flag_string = QLineEdit()
        self.mode_box = QComboBox()
        self.preset_box = QComboBox()
        self.mode_description = QLabel('Pick a Game Mode!')
        self.flag_description = QLabel('Pick a Flag Set!')

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
        self.tab10 = QWidget()

        self.tablist = [
            self.tab1, self.tab2, self.tab3, self.tab4, self.tab5, self.tab6,
            self.tab7, self.tab8, self.tab9, self.tab10
        ]

        # global busy notifications
        self.flags_changing = False

        # Begin building program/window
        # pull data from files
        self.init_flags()

        # create window using geometry data
        self.init_window()

        self.rom_input.setText(self.rom_text)
        self.rom_output.setText(self.rom_output_directory)
        self.update_flag_string()
        # self.updateFlagCheckboxes()
        self.flag_button_clicked()
        self.update_preset_dropdown()
        self.clear_ui()
        self.flag_string.setText(config.get(
            'Settings',
            'default_flagstring',
            fallback='b c d e f g h i m n o p q r s t w y z alphalores improvedpartygear informativemiss magicnumbers '
                     'mpparty nicerpoison questionablecontent regionofdoom tastetherainbow makeover partyparty '
                     'alasdraco capslockoff johnnydmad dancelessons lessfanatical swdtechspeed:faster shadowstays'
        ))

    def init_window(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # build the UI
        self.create_layout()

        previous_rom_path = config.get('Settings', 'input_path', fallback='')
        previous_output_directory = config.get('Settings', 'output_path', fallback='')

        self.rom_text = previous_rom_path
        self.rom_output_directory = previous_output_directory

        # show program onscreen
        self.show()  # maximize the randomizer

        # index = self.presetBox.currentIndex()

    def create_layout(self):
        # Menubar
        file_menu = QMenu('File', self)
        file_menu.addAction('Quit', App.quit)
        self.menuBar().addMenu(file_menu)

        menu_separator = self.menuBar().addMenu('|')
        menu_separator.setEnabled(False)

        if not BETA and update.list_available_updates(refresh=False):
            self.menuBar().addAction('Update Available', update_bc)
        else:
            self.menuBar().addAction('Check for Updates', update_bc)

        # menu_separator2 = self.menuBar().addMenu('|')
        # menu_separator2.setEnabled(False)

        # self.menuBar().addAction('Toggle Dark Mode', toggle_palette)

        # Primary Vertical Box Layout
        vbox = QVBoxLayout()

        title_label = QLabel('Beyond Chaos Randomizer')
        font = QtGui.QFont('Arial', 24, QtGui.QFont.Black)
        title_label.setFont(font)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setMargin(10)
        vbox.addWidget(title_label)

        # rom input and output, seed input, generate button
        vbox.addWidget(self.group_box_one_layout())
        # game mode, preset flag selections and description
        vbox.addWidget(self.group_box_two_layout())
        # flags box
        vbox.addWidget(self.flag_box_layout())

        self.central_widget.setLayout(vbox)
        self.setCentralWidget(self.central_widget)

    # Top groupbox consisting of ROM selection, and Seed number input
    def group_box_one_layout(self):
        group_layout = QGroupBox('Input and Output')

        grid_layout = QGridLayout()

        # ROM INPUT
        label_rom_input = QLabel('ROM File:')
        label_rom_input.setAlignment(QtCore.Qt.AlignRight |
                                     QtCore.Qt.AlignVCenter)
        grid_layout.addWidget(label_rom_input, 1, 1)

        self.rom_input = QLineEdit()
        self.rom_input.setPlaceholderText('Required')
        self.rom_input.setReadOnly(True)
        grid_layout.addWidget(self.rom_input, 1, 2, 1, 3)

        self.label_rom_error = QLabel()
        self.label_rom_error.setStyleSheet('color: darkred;')
        self.label_rom_error.setHidden(True)
        grid_layout.addWidget(self.label_rom_error, 2, 2, 1, 3)

        btn_rom_input = QPushButton('Browse')
        btn_rom_input.setMaximumWidth(self.width)
        btn_rom_input.setMaximumHeight(self.height)
        btn_rom_input.setStyleSheet(
            'font:bold;'
            'font-size:18px;'
            'height:24px;'
            'background-color: #5A8DBE;'
            'color:#E4E4E4;'
        )
        btn_rom_input.clicked.connect(lambda: self.open_file_chooser())
        btn_rom_input.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        btn_rom_input_style = QGraphicsDropShadowEffect()
        btn_rom_input_style.setBlurRadius(3)
        btn_rom_input_style.setOffset(3, 3)
        btn_rom_input.setGraphicsEffect(btn_rom_input_style)
        grid_layout.addWidget(btn_rom_input, 1, 5)

        # ROM OUTPUT
        lbl_rom_output = QLabel('Output Directory:')
        lbl_rom_output.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        grid_layout.addWidget(lbl_rom_output, 3, 1)

        self.rom_output = QLineEdit()
        self.rom_input.textChanged[str].connect(self.validate_input_rom)
        grid_layout.addWidget(self.rom_output, 3, 2, 1, 3)

        btn_rom_output = QPushButton('Browse')
        btn_rom_output.setMaximumWidth(self.width)
        btn_rom_output.setMaximumHeight(self.height)
        btn_rom_output.setStyleSheet(
            'font:bold;'
            'font-size:18px;'
            'height:24px;'
            'background-color:#5A8DBE;'
            'color:#E4E4E4;'
        )
        btn_rom_output.clicked.connect(lambda: self.open_directory_chooser())
        btn_rom_output.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        btn_rom_output_style = QGraphicsDropShadowEffect()
        btn_rom_output_style.setBlurRadius(3)
        btn_rom_output_style.setOffset(3, 3)
        btn_rom_output.setGraphicsEffect(btn_rom_output_style)
        grid_layout.addWidget(btn_rom_output, 3, 5)

        # SEED INPUT
        lbl_seed_input = QLabel('Seed Number:')
        lbl_seed_input.setAlignment(QtCore.Qt.AlignRight |
                                    QtCore.Qt.AlignVCenter)
        grid_layout.addWidget(lbl_seed_input, 4, 1)

        self.seed_input = QLineEdit()
        self.seed_input.setPlaceholderText('Optional')
        grid_layout.addWidget(self.seed_input, 4, 2)

        lbl_seed_count = QLabel('Number to Generate:')
        lbl_seed_count.setAlignment(QtCore.Qt.AlignRight |
                                    QtCore.Qt.AlignVCenter)
        grid_layout.addWidget(lbl_seed_count, 4, 3)

        self.seed_count = QSpinBox()
        self.seed_count.setValue(1)
        self.seed_count.setMinimum(1)
        self.seed_count.setMaximum(99)
        self.seed_count.setFixedWidth(40)
        grid_layout.addWidget(self.seed_count, 4, 4)

        btn_generate = QPushButton('Generate')
        btn_generate.setMinimumWidth(125)
        btn_generate.setMaximumWidth(self.width)
        btn_generate.setMaximumHeight(self.height)
        btn_generate.setStyleSheet(
            'font:bold;'
            'font-size:18px;'
            'height:24px;'
            'background-color:#5A8DBE;'
            'color:#E4E4E4;'
        )
        btn_generate.clicked.connect(lambda: self.generate_seed())
        btn_generate.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        btn_generate_style = QGraphicsDropShadowEffect()
        btn_generate_style.setBlurRadius(3)
        btn_generate_style.setOffset(3, 3)
        btn_generate.setGraphicsEffect(btn_generate_style)
        grid_layout.addWidget(btn_generate, 4, 5)

        group_layout.setLayout(grid_layout)
        return group_layout

    def group_box_two_layout(self):
        self.compile_modes()
        group_mode_and_preset = QGroupBox()
        layout_mode_and_preset = QGridLayout()

        # ---- Game Mode Drop Down ---- #
        label_game_mode = QLabel('Game Mode:')
        label_game_mode.setStyleSheet('padding-left: 22px;')
        layout_mode_and_preset.addWidget(label_game_mode, 1, 1)
        for item in self.game_modes.items():
            self.mode_box.addItem(item[0])
        self.mode_box.currentTextChanged.connect(
            lambda: self.update_game_description()
        )
        layout_mode_and_preset.addWidget(self.mode_box, 1, 2)

        # ---- Preset Flags Drop Down ---- #
        label_preset_mode = QLabel('Preset Flags:')
        label_preset_mode.setStyleSheet('padding-left: 22px;')
        layout_mode_and_preset.addWidget(label_preset_mode, 1, 3)
        self.preset_box.addItem('Select a flag set')
        self.load_saved_flags()
        for key in self.game_presets.keys():
            self.preset_box.addItem(key)

        self.preset_box.currentTextChanged.connect(
            lambda: self.update_preset_dropdown()
        )
        layout_mode_and_preset.addWidget(self.preset_box, 1, 4)

        label_flag_description = QLabel('Preset Description:')
        label_flag_description.setStyleSheet(
            'font-size:14px;'
            'height:24px;'
            'color:#253340;'
            'padding-left: 22px;'
        )
        layout_mode_and_preset.addWidget(label_flag_description, 1, 5)

        self.flag_description.setStyleSheet(
            'font-size:14px;'
            'height:24px;'
            'color:#253340;'
        )
        layout_mode_and_preset.addWidget(self.flag_description, 1, 6)

        layout_mode_and_preset.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        group_mode_and_preset.setLayout(layout_mode_and_preset)
        group_mode_and_preset.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        return group_mode_and_preset

    def flag_box_layout(self):
        group_box_two = QGroupBox()
        middle_h_box = QHBoxLayout()
        middle_right_group_box = QGroupBox('Flag Selection')
        layout_tab_v_box = QVBoxLayout()
        tabs = QTabWidget()
        tabs.setElideMode(True)  # Tabs shrink in size to fit all tabs on screen

        # loop to add tab objects to 'tabs' TabWidget
        for t, d, names in zip(self.tablist,
                               self.dictionaries,
                               self.tab_names):
            tab_obj = QScrollArea()
            tabs.addTab(tab_obj, names)
            tab_layout = QGridLayout()
            flag_count = 0
            current_row = 0
            tab_layout.setColumnStretch(4, 1)  # Long description should use as much space as possible
            tab_layout.setVerticalSpacing(0)

            for flag_name, flag in d.items():
                margin_top = QSpacerItem(0, spacer_fixed_height)
                tab_layout.addItem(margin_top, current_row, 0)
                current_row += 1

                if flag.input_type == 'float2':
                    flag_control = QDoubleSpinBox()
                    flag_control.setMinimum(float(flag.minimum_value))
                    flag_control.default = float(flag.default_value)
                    flag_control.setMaximum(float(flag.maximum_value))
                    flag_control.setSingleStep(.1)
                    flag_control.setSpecialValueText('Random')
                    flag_control.setValue(flag_control.default)
                    flag_control.text = flag_name
                    flag_control.setFixedWidth(control_fixed_width)
                    flag_control.setMinimumHeight(0)
                    flag_control.setFixedHeight(control_fixed_height)
                    flag_label = QLabel(f'{flag_name}')

                    if not flag.name == 'randomboost':
                        flag_control.setSuffix('x')

                    flag_control.valueChanged.connect(lambda: self.flag_button_clicked())
                    flag_count += 1
                elif flag.input_type == 'integer':
                    flag_control = QSpinBox()
                    flag_control.default = int(flag.default_value)
                    flag_control.setMinimum(int(flag.minimum_value))
                    flag_control.setMaximum(int(flag.maximum_value))
                    flag_control.setFixedWidth(control_fixed_width)
                    flag_control.setMinimumHeight(0)
                    flag_control.setFixedHeight(control_fixed_height)
                    flag_control.setValue(flag_control.default)
                    flag_control.text = flag_name
                    flag_label = QLabel(f'{flag_name}')

                    if flag_name == 'cursepower' or flag_name == 'levelcap':
                        flag_control.setSpecialValueText('Random')
                    else:
                        flag_control.setSpecialValueText('Off')

                    flag_control.valueChanged.connect(lambda: self.flag_button_clicked())
                    flag_count += 1
                elif flag.input_type == 'combobox':
                    flag_control = QComboBox()
                    flag_control.addItems(flag.choices)
                    flag_control.text = flag_name
                    flag_control.setFixedWidth(control_fixed_width)
                    flag_control.setMinimumHeight(0)
                    flag_control.setFixedHeight(control_fixed_height)
                    flag_control.setCurrentIndex(flag.default_index)

                    if self.makeover_groups and flag_name in self.makeover_groups:
                        flag_label = QLabel(f'{flag_name} (' + str(self.makeover_groups[flag_name]) +
                                            ')')
                    else:
                        flag_label = QLabel(f'{flag_name}')

                    flag_control.activated[str].connect(lambda: self.flag_button_clicked())
                    flag_count += 1
                else:
                    # Assume boolean
                    flag_control = QPushButton('No')
                    self.check_boxes.append(flag_control)
                    flag_control.setFixedWidth(control_fixed_width)
                    flag_control.setMinimumHeight(0)
                    flag_control.setFixedHeight(control_fixed_height)
                    flag_control.setCheckable(True)
                    flag_control.value = flag_name
                    flag_label = QLabel(f'{flag_name}')

                    if (flag_name == 'remonsterate' and not len(check_remonsterate()) == 0) or \
                            (flag_name == 'makeover' and not len(check_player_sprites()) == 0):
                        flag_control.setEnabled(False)

                    flag_control.clicked.connect(lambda checked: self.flag_button_clicked())
                    flag_count += 1

                flag_description = QLabel(f'{flag.long_description}')
                flag_description.setWordWrap(True)
                flag_control.flag = flag
                flag.controls = [flag_control, flag_label, flag_description]
                # flag_control.setStyleSheet('background-color: red')
                # flag_label.setStyleSheet('background-color: blue')
                # flag_description.setStyleSheet('background-color: green')

                tab_layout.addWidget(flag_control, current_row, 1)
                tab_layout.addWidget(flag_label, current_row, 2)
                tab_layout.addWidget(flag_description, current_row, 4)
                current_row += 1

                margin_bottom = QSpacerItem(0, spacer_fixed_height)
                tab_layout.addItem(margin_bottom, current_row, 0)
                current_row += 1

                flag.margins = [margin_top, margin_bottom]

                h_spacer = QFrame()
                h_spacer.setFrameShape(QFrame.HLine)
                h_spacer.setFrameShadow(QFrame.Sunken)
                if not flag_count == len(d):
                    h_spacer.setFixedHeight(2)
                    h_spacer.setStyleSheet('margin: 0 2px 0 2px;')
                    tab_layout.addWidget(h_spacer, current_row, 0, 0, 6)
                    flag.controls.append(h_spacer)
                    current_row += 1
                else:
                    # Fake row set to stretch as much as possible. Keeps other rows from stretching.
                    h_spacer.setStyleSheet('display:none;')
                    tab_layout.addWidget(h_spacer, current_row, 0, 0, 6)
                    tab_layout.setRowStretch(current_row, 1)
                    current_row += 1

            v_spacer = QFrame()
            v_spacer.setFrameShape(QFrame.VLine)
            v_spacer.setFrameShadow(QFrame.Sunken)
            v_spacer.setFixedWidth(5)
            v_spacer.setStyleSheet('margin: 5px 0 0 0;')
            tab_layout.addWidget(v_spacer, 0, 3, flag_count * 4 - 1, 1)

            t.setLayout(tab_layout)
            tab_obj.setWidgetResizable(True)
            tab_obj.setWidget(t)

        layout_tab_v_box.addWidget(tabs)

        # This is the line in the layout that displays the string
        # of selected flags and the button to save those flags
        widget_v = QWidget()
        widget_v_box_layout = QVBoxLayout()
        widget_v.setLayout(widget_v_box_layout)

        widget_v_box_layout.addWidget(QLabel('Text-string of selected flags:'))
        self.flag_string.textChanged.connect(self.text_changed)
        widget_v_box_layout.addWidget(self.flag_string)

        btn_save = QPushButton('Save flags selection')
        btn_save.clicked.connect(lambda: self.save_flags())
        widget_v_box_layout.addWidget(btn_save)

        # This part makes a group box and adds the selected-flags
        # display and a button to clear the UI
        widget_flag_text = QGroupBox()
        flag_text_h_box = QHBoxLayout()
        flag_text_h_box.addWidget(widget_v)
        btn_clear_ui = QPushButton('Reset')
        btn_clear_ui.setStyleSheet('font-size:12px; height:60px')
        btn_clear_ui.clicked.connect(lambda: self.clear_ui())
        flag_text_h_box.addWidget(btn_clear_ui)
        widget_flag_text.setLayout(flag_text_h_box)

        layout_tab_v_box.addWidget(widget_flag_text)
        middle_right_group_box.setLayout(layout_tab_v_box)
        # ------------- Part two (right) end ------------------------

        # Add widgets to HBoxLayout and assign to middle groupbox
        # layout
        middle_h_box.addWidget(middle_right_group_box)
        group_box_two.setLayout(middle_h_box)

        return group_box_two

    # ---------------------------------------------------------------
    # ------------ NO MORE LAYOUT DESIGN PAST THIS POINT-------------
    # ---------------------------------------------------------------

    def get_missing_requirements(self, flag: Flag, current_index: int = 0) -> str | bool:
        """
        Takes a flag and analyzes it's requirements to see if the requirements are met.

        For the original method call (as indicated by current_index == 0, the method returns a string
            representing the error message to be displayed on the GUI. Or an empty string, if all requirements
            are met.

        This method also calls itself recursively for each item in the Flag's requirements. These recursive
            calls return True or False depending on whether or not the requirements were met for that part of
            the requirements.
        Returns:
            str
            bool

        TODO: Change this into a Flag class method utilizing flag.value instead of the value of a PyQt5 control
        """
        requirements = flag.requirements

        if not requirements:
            return ''

        if len(requirements) <= current_index:
            return False

        result = True

        for required_flag, required_value in requirements[current_index].items():
            try:
                flag_control = Options_.get_flag(required_flag).controls[0]
                flag_value = None
                if isinstance(flag_control, QPushButton):
                    flag_value = flag_control.isChecked()
                elif isinstance(flag_control, QSpinBox) or isinstance(flag_control, QDoubleSpinBox):
                    flag_value = round(flag_control.value(), 2)
                elif isinstance(flag_control, QComboBox):
                    flag_value = flag_control.currentText()
                if not flag_value == required_value:
                    result = False
                    break
            except AttributeError:
                continue

        result = result or self.get_missing_requirements(flag, current_index + 1)

        if current_index > 0:
            return result
        if current_index == 0 and not result:
            return flag.get_requirement_string()
        return ''

    def text_changed(self, text):
        if self.flags_changing:
            return
        self.flags_changing = True
        self.clear_controls()
        values = text.split(' ')
        self.flags.clear()
        self.flag_string.clear()
        self.conflicts = {}
        self.requirements = {}
        children = []
        for t in self.tablist:
            children.extend(t.children())
        children = [c for c in children if isinstance(c, QPushButton) or isinstance(c, QSpinBox)
                    or isinstance(c, QDoubleSpinBox) or isinstance(c, QComboBox)]
        for child in children:
            child.setStyleSheet('background-color: white; border: none;')
            if child.isEnabled():
                if isinstance(child, QPushButton):
                    for v in values:
                        if str(v).lower() == child.value:
                            child.setChecked(True)
                            child.setText('Yes')
                            child.setStyleSheet('background-color: #CCE4F7; border: 1px solid darkblue;')
                            self.flags.append(child.value)

                            for flag_name in child.flag.conflicts:
                                try:
                                    self.conflicts[flag_name].append(child.flag.name)
                                except KeyError:
                                    self.conflicts[flag_name] = [child.flag.name]
                    handle_children(child.flag, child.isChecked())
                elif isinstance(child, QSpinBox):
                    for v in values:
                        if ':' in v and child.text.lower() == str(v).split(':')[0]:
                            try:
                                child.setValue(int(str(v).split(':')[1]))
                            except ValueError:
                                if str(v).split(':')[1] == child.specialValueText().lower():
                                    child.setValue(child.minimum())

                            child.setStyleSheet('background-color: #CCE4F7; border: 1px solid darkblue;')
                            self.flags.append(v)

                            for flag_name in child.flag.conflicts:
                                try:
                                    self.conflicts[flag_name].append(child.flag.name)
                                except KeyError:
                                    self.conflicts[flag_name] = [child.flag.name]
                    handle_children(child.flag, round(child.value(), 2))
                elif isinstance(child, QDoubleSpinBox):
                    for v in values:
                        if ':' in v and child.text.lower() == str(v).split(':')[0]:
                            try:
                                value = float(str(v).split(':')[1])
                                if value >= 0:
                                    child.setValue(value)
                            except ValueError:
                                if str(v).split(':')[1] == child.specialValueText().lower():
                                    child.setValue(child.minimum())
                            child.setStyleSheet('background-color: #CCE4F7; border: 1px solid darkblue;')
                            self.flags.append(v)

                            for flag_name in child.flag.conflicts:
                                try:
                                    self.conflicts[flag_name].append(child.flag.name)
                                except KeyError:
                                    self.conflicts[flag_name] = [child.flag.name]
                    handle_children(child.flag, round(child.value(), 2))
                elif isinstance(child, QComboBox):
                    for v in values:
                        if ':' in v and child.text.lower() == str(v).split(':')[0]:
                            index_of_value = child.findText(str(v).split(':')[1], QtCore.Qt.MatchFixedString)
                            child.setCurrentIndex(index_of_value)
                            child.setStyleSheet('background-color: #CCE4F7; border: 1px solid darkblue;')
                            self.flags.append(v)

                            for flag_name in child.flag.conflicts:
                                try:
                                    self.conflicts[flag_name].append(child.flag.name)
                                except KeyError:
                                    self.conflicts[flag_name] = [child.flag.name]
                    handle_children(child.flag, child.currentText())
        for child in children:
            self.requirements[child.flag.name] = self.get_missing_requirements(child.flag)

        handle_conflicts_and_requirements(self.conflicts, self.requirements)
        self.update_flag_string()
        self.flags_changing = False

    # (At startup) Opens reads code flags/descriptions and
    #   puts data into separate dictionaries
    def init_flags(self):
        for flag in sorted(NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS, key=lambda x: x.name):
            if flag.category == 'core':
                d = self.flag
            elif flag.category == 'quality_of_life':
                d = self.quality_of_life
            elif flag.category == 'aesthetic':
                d = self.aesthetic
            elif flag.category == 'sprite':
                d = self.sprite
            elif flag.category == 'spriteCategories':
                d = self.sprite_categories
            elif flag.category == 'experimental':
                d = self.experimental
            elif flag.category == 'gamebreaking':
                d = self.gamebreaking
            elif flag.category == 'field':
                d = self.field
            elif flag.category == 'characters':
                d = self.characters
            elif flag.category == 'beta':
                d = self.beta
            elif flag.category == 'battle':
                d = self.battle
            else:
                print(f'Flag {flag.name} does not have a valid category.')
                continue

            d[flag.name] = flag

    # opens input dialog to get a name to assign a desired seed flag set, then
    # saves flags and selected mode to the cfg file
    def save_flags(self):
        text, ok_pressed = QInputDialog.getText(
            self,
            'Save Seed',
            'Enter a name for this flag set',
            QLineEdit.Normal,
            ''
        )
        if ok_pressed and text != '':
            self.game_presets[text] = (
                    self.flag_string.text() + '|' + self.mode
            )
            write_flags(
                text,
                (self.flag_string.text() + '|' + self.mode)
            )
            index = self.preset_box.findText(text)
            if index == -1:
                self.preset_box.addItem(text)
            else:
                self.preset_box.removeItem(index)
                self.preset_box.addItem(text)

            index = self.preset_box.findText(text)
            self.preset_box.setCurrentIndex(index)

    def load_saved_flags(self):
        flag_set = read_flags()
        if flag_set is not None:
            for text, flags in flag_set.items():
                self.game_presets[text] = flags

    def update_game_description(self):
        self.mode_description.clear()
        modes = {0: ('Normal', 'normal'),
                 1: ('Race - Kefka @ Narshe', 'katn'),
                 2: ('Ancient Cave', 'ancientcave'),
                 3: ('Speed Cave', 'speedcave'),
                 4: ('Race - Randomized Cave', 'racecave'),
                 5: ('Race - Dragon Hunt', 'dragonhunt'),
                 }
        index = self.mode_box.currentIndex()
        self.mode_description.setText(modes.get(index, 'Pick a Game Mode!')[0])
        self.mode = \
            [x[1] for x in modes.values() if x[1] == modes.get(index)[1]][0]

    def update_preset_dropdown(self):

        modes = {0: ('Normal', 'normal'),
                 1: ('Race - Kefka @ Narshe', 'katn'),
                 2: ('Ancient Cave', 'ancientcave'),
                 3: ('Speed Cave', 'speedcave'),
                 4: ('Race - Randomized Cave', 'racecave'),
                 5: ('Race - Dragon Hunt', 'dragonhunt')}
        text = self.preset_box.currentText()
        index = self.preset_box.findText(text)
        flags = self.game_presets.get(text)
        if index == 0:
            self.clear_ui()
            self.flag_description.clear()
            self.flag_description.setText('Pick a flag set!')
        elif index == 1:
            self.flag_description.setText('Flags designed for a new player')
            self.flag_string.setText(flags)
            self.mode = 'normal'
            self.mode_box.setCurrentIndex(0)
        elif index == 2:
            self.flag_description.setText(
                'Flags designed for an intermediate player'
            )
            self.flag_string.setText(flags)
            self.mode = 'normal'
            self.mode_box.setCurrentIndex(0)
        elif index == 3:
            self.flag_description.setText(
                'Flags designed for an advanced player'
            )
            self.flag_string.setText(flags)
            self.mode = 'normal'
            self.mode_box.setCurrentIndex(0)
        elif index == 4:
            self.flag_description.setText(
                'Flags designed for a chaotic player'
            )
            self.flag_string.setText(flags)
            self.mode = 'normal'
            self.mode_box.setCurrentIndex(0)
        elif index == 5:
            self.flag_description.setText(
                'Flags designed for KaN easy difficulty races'
            )
            self.flag_string.setText(flags)
            self.mode = 'katn'
            self.mode_box.setCurrentIndex(1)
        elif index == 6:
            self.flag_description.setText(
                'Flags designed for KaN medium difficulty races'
            )
            self.flag_string.setText(flags)
            self.mode = 'katn'
            self.mode_box.setCurrentIndex(1)
        elif index == 7:
            self.flag_description.setText(
                'Flags designed for KaN insane difficulty races'
            )
            self.flag_string.setText(flags)
            self.mode = 'katn'
            self.mode_box.setCurrentIndex(1)
        else:
            custom_flags = flags.split('|')[0]
            mode = flags.split('|')[1]
            self.flag_description.setText('Custom saved flags')
            self.flag_string.setText(custom_flags)
            self.mode = mode
            self.mode_box.setCurrentIndex(
                [k for k, v in modes.items() if v[1] == mode][0]
            )

    def clear_ui(self):
        self.seed = ''
        self.flags.clear()
        self.seed_input.setText(self.seed)

        self.mode_box.setCurrentIndex(0)
        self.preset_box.setCurrentIndex(0)
        self.init_flags()
        self.clear_controls()
        self.flag_string.clear()
        self.flags.clear()
        handle_conflicts_and_requirements({}, {})
        self.update_game_description()

    def clear_controls(self):
        for tab in self.tablist:
            for child in tab.children():
                if type(child) == QPushButton:
                    child.setChecked(False)
                    child.setText('No')
                elif type(child) == QSpinBox or type(child) == QDoubleSpinBox:
                    child.setValue(child.default)
                elif type(child) == QComboBox:
                    child.setCurrentIndex(child.flag.default_index)

    # When flag UI button is checked, update corresponding
    # dictionary values
    def flag_button_clicked(self):
        # Check self.flagsChanging first. If that is set, a new flag preset has been selected, which is causing
        #  the controls to change and call this method. But we do not want to do anything then, otherwise it can
        #  add duplicate entries to the flag string
        if not self.flags_changing:
            self.flags.clear()
            self.conflicts = {}
            self.requirements = {}
            all_children = []
            for t, d in zip(self.tablist, self.dictionaries):
                children = t.findChildren(QPushButton)
                for c in children:
                    all_children.append(c)
                    if c.isChecked():
                        c.setStyleSheet('background-color: #CCE4F7; border: 1px solid darkblue;')
                        c.setText('Yes')
                        self.flags.append(c.value)
                        for flag_name in c.flag.conflicts:
                            try:
                                self.conflicts[flag_name].append(c.flag.name)
                            except KeyError:
                                self.conflicts[flag_name] = [c.flag.name]
                    else:
                        c.setStyleSheet('background-color: white; border: none;')
                        c.setText('No')
                    handle_children(c.flag, c.isChecked())
                children = t.findChildren(QSpinBox) + t.findChildren(QDoubleSpinBox)
                for c in children:
                    all_children.append(c)
                    if not round(c.value(), 1) == c.default:
                        c.setStyleSheet('background-color: #CCE4F7; border: 1px solid darkblue;')
                        if round(c.value(), 2) == c.minimum():
                            self.flags.append(c.text + ':random')
                        else:
                            self.flags.append(c.text + ':' + str(round(c.value(), 2)))
                        for flag_name in c.flag.conflicts:
                            try:
                                self.conflicts[flag_name].append(c.flag.name)
                            except KeyError:
                                self.conflicts[flag_name] = [c.flag.name]
                    else:
                        c.setStyleSheet('background-color: white; border: none;')
                    handle_children(c.flag, round(c.value(), 2))
                children = t.findChildren(QComboBox)
                for c in children:
                    all_children.append(c)
                    if c.currentIndex() != c.flag.default_index:
                        c.setStyleSheet('background-color: #CCE4F7; border: 1px solid darkblue;')
                        self.flags.append(c.text.lower() + ':' + c.currentText().lower())

                        for flag_name in c.flag.conflicts:
                            try:
                                self.conflicts[flag_name].append(c.flag.name)
                            except KeyError:
                                self.conflicts[flag_name] = [c.flag.name]
                    else:
                        c.setStyleSheet('background-color: white; border: none;')
                    handle_children(c.flag, c.currentText())
            for child in all_children:
                self.requirements[child.flag.name] = self.get_missing_requirements(child.flag)

            handle_conflicts_and_requirements(self.conflicts, self.requirements)
            self.update_flag_string()

    # Opens file dialog to select rom file and assigns it to value in
    # parent/Window class
    def open_file_chooser(self):
        file_path = QFileDialog.getOpenFileName(
            self,
            'Open File',
            './',
            filter='ROMs (*.smc *.sfc *.fig);;All Files(*.*)'
        )

        # display file location in text input field
        self.rom_input.setText(str(file_path[0]))

    def open_directory_chooser(self):
        file_path = QFileDialog.getExistingDirectory(self, 'Open File', './')

        # display file location in text input field
        self.rom_output.setText(str(file_path))

    def compile_modes(self):
        for mode in self.supported_game_modes:
            if mode == 'normal':
                self.game_modes['Normal'] = (
                    'Play through the normal story with randomized gameplay.'
                )
            elif mode == 'katn':
                self.game_modes['Race - Kefka @ Narshe'] = (
                    'Race through the story and defeat Kefka at Narshe'
                )
            elif mode == 'ancientcave':
                self.game_modes['Ancient Cave'] = (
                    'Play though a long randomized dungeon.'
                )
            elif mode == 'speedcave':
                self.game_modes['Speed Cave'] = (
                    'Play through a medium randomized dungeon.'
                )
            elif mode == 'racecave':
                self.game_modes['Race - Randomized Cave'] = (
                    'Race through a short randomized dungeon.'
                )
            elif mode == 'dragonhunt':
                self.game_modes['Race - Dragon Hunt'] = (
                    'Race to kill all 8 dragons.'
                )

    # Get seed generation parameters from UI to prepare for
    # seed generation. This will show a confirmation dialog,
    # and call the local Randomizer.py file and pass arguments
    # to it
    def generate_seed(self):

        self.rom_text = self.rom_input.text()

        # Check to see if the supplied output directory exists.
        if os.path.isdir(self.rom_output.text()):
            # It does, use that directory.
            self.rom_output_directory = self.rom_output.text()
        elif self.rom_output.text() == '':
            # It does not, but the text box is blank. Use the
            # directory that the ROM file is in.
            self.rom_output_directory = self.rom_output.placeholderText()
        else:
            # The supplied path is invalid. Raise an error.
            QMessageBox.about(
                self,
                'Error',
                'That output directory does not exist.'
            )
            return

        if self.rom_text == '':
            QMessageBox.about(
                self,
                'Error',
                'You need to select a FFVI rom!'
            )
        else:
            if not os.path.exists(self.rom_text):
                self.rom_input.setText('')
                QMessageBox.about(
                    self,
                    'Error',
                    f'No ROM was found at the path {str(self.rom_text)}. Please choose a different ROM file.'
                )
                return
            try:
                f = open(self.rom_text, 'rb')
                data = f.read()
                f.close()
                md5_hash = hashlib.md5(data).hexdigest()
                if md5_hash not in utils.WELL_KNOWN_ROM_HASHES:
                    confirm_hash = QMessageBox.question(
                        self,
                        'WARNING!',
                        'The md5 hash of this file does not match the known hashes of the english FF6 1.0 rom!'
                        + os.linesep
                        + 'Continue Anyway?',
                        QMessageBox.Yes | QMessageBox.Cancel
                    ) == QMessageBox.Yes
                    if not confirm_hash:
                        return
            except IOError as io_exception:
                QMessageBox.about(self, 'Error', str(io_exception))
                return

            self.seed = self.seed_input.text()

            display_seed = self.seed

            flag_msg = ''

            if self.seed == '':
                display_seed = '(none)'

            flag_mode = ''
            for flag in self.flags:
                flag_mode += ' ' + flag

                flag_msg = ''
            flag_mode = flag_mode.strip()
            for flag in self.flags:
                if flag_msg:
                    if len(flag) == 1:
                        flag_msg += ' '
                    else:
                        flag_msg += '\n'
                flag_msg += flag
            if flag_msg == '':
                QMessageBox.about(
                    self,
                    'Error',
                    'You need to select a flag!'
                )
                return

            if 'bingoboingo' in self.flags:
                bingo = BingoPrompts()
                bingo.setModal(True)
                bingo.exec()

                bingotype = ''
                if bingo.abilities:
                    bingotype += 'a'
                if bingo.items:
                    bingotype += 'i'
                if bingo.monsters:
                    bingotype += 'm'
                if bingo.spells:
                    bingotype += 's'

                if bingotype != '':
                    self.bingo_type = bingotype
                else:
                    return
                self.bingo_diff = bingo.difficulty
                self.bingo_size = bingo.grid_size
                self.bingo_cards = bingo.num_cards

            # This makes the flag string more readable in
            # the confirm dialog
            message = (
                '{0: <10} {1}\n'
                '{2: <9} {3}\n'
                '{4: <10} {5}\n'
                '{6: <10} {7}\n'
                '{8: <10} {9}\n'
                '{10: <10}'.format(
                    'Rom:', self.rom_text,
                    'Output:', self.rom_output_directory,
                    'Seed:', display_seed,
                    'Batch:', self.seed_count.text(),
                    'Mode:', self.mode,
                    'Flags:')
            )
            flag_message = QLabel(f'{flag_msg}')
            flag_message.setStyleSheet('margin-left: 2px;')
            continue_confirmed = QDialogScroll(
                title='Confirm Seed Generation?',
                header=message,
                scroll_contents=flag_message,
                left_button='Cancel',
                right_button='Confirm',
                icon=QStyle.SP_MessageBoxQuestion
            ).exec()
            if continue_confirmed:
                self.clear_console()
                self.seed = self.seed or int(time.time())
                seeds_to_generate = int(self.seed_count.text())
                result_files = []
                for currentSeed in range(seeds_to_generate):
                    print('Rolling seed ' + str(currentSeed + 1) + ' of ' + str(seeds_to_generate) + '.')
                    # User selects confirm/accept/yes option
                    bundle = f'{self.version}|{self.mode}|{flag_mode}|{self.seed}'
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
                            'infile_rom_path': self.rom_text,
                            'outfile_rom_path': self.rom_output_directory,
                            'seed': bundle,
                            'bingo_type': self.bingo_type,
                            'bingo_size': self.bingo_size,
                            'bingo_difficulty': self.bingo_diff,
                            'bingo_cards': self.bingo_cards,
                            'application': 'gui'
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
                                raise RuntimeError('Unexpected error: The process performing randomization died.')
                            if parent_connection.poll(timeout=5):
                                child_output = parent_connection.recv()
                            else:
                                child_output = None
                            if child_output:
                                try:
                                    if isinstance(child_output, str):
                                        print(child_output)
                                    elif isinstance(child_output, Exception):
                                        raise child_output
                                    elif isinstance(child_output, bool):
                                        break
                                except EOFError:
                                    break

                        # generate the output file name since we're using subprocess now instead of a direct call
                        if '.' in self.rom_text:
                            temp_name = os.path.basename(self.rom_text).rsplit('.', 1)
                        else:
                            temp_name = [os.path.basename(self.rom_text), 'smc']
                        seed = bundle.split('|')[-1]
                        result_file = os.path.join(self.rom_output_directory,
                                                   '.'.join([os.path.basename(temp_name[0]),
                                                             str(seed), temp_name[1]]))
                        if self.seed:
                            self.seed = str(int(self.seed) + 1)
                    except Exception as gen_exception:
                        traceback.print_exc()
                        gen_traceback = QTextEdit(
                            '<br>'.join(traceback.format_exc().splitlines())
                        )
                        gen_traceback.setStyleSheet('background-color: rgba(0,0,0,0); border: none;')
                        gen_traceback.setReadOnly(True)
                        QDialogScroll(
                            title=f'Exception: {str(type(gen_exception).__name__)}',
                            header=f'A {str(type(gen_exception).__name__)} ' +
                                   'exception occurred '
                                   'that prevented randomization: ' +
                                   '<br>' +
                                   '<br>' +
                                   'Please submit the following traceback over at the '
                                   '<a href="https://discord.gg/ZCHZp7qxws">Beyond Chaos Barracks discord</a> '
                                   'bugs channel:' +
                                   '<br>',
                            scroll_contents=gen_traceback,
                            right_button='Close',
                            icon=QStyle.SP_MessageBoxCritical
                        ).exec()
                    else:
                        result_files.append(result_file)
                        if currentSeed + 1 == seeds_to_generate:
                            # If generation succeeded, set the default flagstring to the last one used.
                            set_config_value('Settings', 'default_flagstring', self.flag_string.text())

                            if seeds_to_generate == 1:
                                QMessageBox.information(
                                    self,
                                    'Successfully created ROM',
                                    f'Result file\n------------\n{result_file}',
                                    QMessageBox.Ok
                                )
                            elif seeds_to_generate > 10:
                                QMessageBox.information(
                                    self,
                                    f'Successfully created {seeds_to_generate} ROMs',
                                    f'{seeds_to_generate} ROMs have been created in {self.rom_output_directory}.',
                                    QMessageBox.Ok
                                )
                            else:
                                result_files_string = '\n------------\n'.join(result_files)
                                QMessageBox.information(
                                    self,
                                    f'Successfully created {seeds_to_generate} ROMs',
                                    f'Result files\n------------\n{result_files_string}',
                                    QMessageBox.Ok
                                )
                        else:
                            self.clear_console()

                    finally:
                        currentSeed += 1

    # Read each dictionary and update text field
    # showing flag codes based upon
    # flags denoted as 'True'
    def update_flag_string(self):
        self.flags_changing = True
        self.flag_string.clear()
        temp = ''
        for x in range(0, len(self.flags)):
            flag = self.flags[x]
            temp += flag + ' '
        self.flag_string.setText(temp)
        self.flags_changing = False

    def validate_input_rom(self, value):
        try:
            if not value == '':
                try:
                    with open(value, 'rb') as rom_file:
                        rom_hash = md5(rom_file.read()).hexdigest()
                    if rom_hash in [MD5HASHNORMAL, MD5HASHTEXTLESS, MD5HASHTEXTLESS2]:
                        self.label_rom_error.setHidden(True)
                    else:
                        self.label_rom_error.setText('WARNING! The selected file does not match supported '
                                                     'English FF3/FF6 v1.0 ROM files!')
                        self.label_rom_error.setHidden(False)
                except FileNotFoundError:
                    self.rom_input.setText('')
                    self.rom_input.setPlaceholderText('')
                    self.label_rom_error.setText('The previously used ROM file could not be found. Please select a '
                                                 'new FF6 ROM file.')
                    self.label_rom_error.setHidden(False)

            self.rom_output.setPlaceholderText(os.path.dirname(os.path.normpath(value)))
        except ValueError:
            pass

    @staticmethod
    def clear_console():
        os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == '__main__':
    multiprocessing.freeze_support()
    args = sys.argv
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    App = QApplication(sys.argv)
    if len(args) > 1 and args[1] == 'update':
        # Continue the updating process after updating the core files.
        if os.path.isfile(os.path.join(os.getcwd(), 'beyondchaos.old.exe')):
            os.remove(os.path.join(os.getcwd(), 'beyondchaos.old.exe'))
        if os.path.isfile(os.path.join(os.getcwd(), 'beyondchaos_console.old.exe')):
            os.remove(os.path.join(os.getcwd(), 'beyondchaos_console.old.exe'))
        update_bc(suppress_prompt=True)
    # QApplication.setStyle('fusion')
    # set_palette()
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
    try:
        if not BETA:
            # We want to present the Welcome screen if the user does not have a config file
            if check_ini():
                first_time_setup = QMessageBox()
                first_time_setup.setIcon(QMessageBox.Information)
                first_time_setup.setWindowTitle('First Time Setup')
                first_time_setup.setText('<b>Welcome to Beyond Chaos Community Edition!</b>' +
                                         '<br>' +
                                         '<br>' +
                                         'As part of first time setup, '
                                         'we need to download the required custom '
                                         'sprite files and folders for randomization.'
                                         '<br>' +
                                         '<br>' +
                                         'Press OK to launch the updater to download the required files.'
                                         '<br>' +
                                         'Press Close to exit the program.')
                first_time_setup.setStandardButtons(QMessageBox.Ok | QMessageBox.Close)
                # first_time_setup.button(QMessageBox.Close).hide()
                button_clicked = first_time_setup.exec()
                if button_clicked == QMessageBox.Close:
                    sys.exit()
                elif button_clicked == QMessageBox.Ok:
                    update_bc(suppress_prompt=True, force_download=True)

            # If required files are missing, display a different message.
            missing_required_files = update.validate_required_files()
            while missing_required_files is not None:
                validation_message = QMessageBox()
                validation_message.setIcon(QMessageBox.Critical)
                validation_message.setWindowTitle('Required Files Missing')
                validation_message.setText('<b>Welcome to Beyond Chaos Community Edition!</b>' +
                                           '<br>' +
                                           '<br>' +
                                           'Files required for the randomizer to function are currently missing: ' +
                                           '<br>' +
                                           '<br>'.join(missing_required_files) +
                                           '<br>' +
                                           '<br>' +
                                           'Press OK to launch the updater to download the required files.'
                                           '<br>' +
                                           'Press Close to exit the program.')
                validation_message.setStandardButtons(QMessageBox.Ok | QMessageBox.Close)
                # validation_message.button(QMessageBox.Close).hide()
                button_clicked = validation_message.exec()
                if button_clicked == QMessageBox.Close:
                    sys.exit()
                elif button_clicked == QMessageBox.Ok:
                    update_bc(suppress_prompt=True, force_download=True)
                    missing_required_files = update.validate_required_files()

            available_updates = update.list_available_updates(refresh=True)
            skip_updates = config.get('Settings', 'updates_hidden', fallback='False')
            if available_updates and skip_updates.lower() == 'false':
                while available_updates:
                    update_message = QMessageBox()
                    update_message.setIcon(QMessageBox.Question)
                    update_message.setWindowTitle('Update Available')
                    update_message.setText('Updates to Beyond Chaos are available!' +
                                           '<br>' +
                                           '<br>' +
                                           str('<br><br>'.join(available_updates)) +
                                           '<br>' +
                                           '<br>' +
                                           'Press OK to launch the updater or Close to skip updating. '
                                           'This pop-up will only show once per update.')

                    update_message.setStandardButtons(QMessageBox.Close | QMessageBox.Ok)
                    button_clicked = update_message.exec()
                    if button_clicked == QMessageBox.Close:
                        # Update_message informs the user about the update button on the UI.
                        update_message.close()
                        update_dismiss_message = QMessageBox()
                        update_dismiss_message.setIcon(QMessageBox.Information)
                        update_dismiss_message.setWindowTitle('Information')
                        update_dismiss_message.setText('The update will be available using '
                                                       "the Update button on the randomizer's menu bar.")
                        update_dismiss_message.setStandardButtons(QMessageBox.Close)
                        button_clicked = update_dismiss_message.exec()
                        if button_clicked == QMessageBox.Close:
                            update_dismiss_message.close()
                            set_config_value('Settings', 'updates_hidden', str(True))
                            break
                    elif button_clicked == QMessageBox.Ok:
                        update_bc(suppress_prompt=True)
                        available_updates = update.list_available_updates(refresh=True)

        window = Window()
        sys.exit(App.exec())
    except Exception as e:
        error_message = QMessageBox()
        error_message.setIcon(QMessageBox.Critical)
        error_message.setWindowTitle('Exception: ' + str(type(e).__name__))
        error_message.setText('A fatal ' + str(type(e).__name__) + ' exception occurred: ' +
                              str(e) +
                              '<br>' +
                              '<br>' +
                              '<br>' +
                              '<br>' +
                              '<b><u>Error Traceback for the Devs</u></b>:' +
                              '<br>' +
                              '<br>' +
                              '<br>'.join(traceback.format_exc().splitlines()))
        error_message.setStandardButtons(QMessageBox.Close)
        button_clicked = error_message.exec()
        if button_clicked == QMessageBox.Close:
            error_message.close()
        traceback.print_exc()
