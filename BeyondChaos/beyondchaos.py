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
        QApplication, QCheckBox, QComboBox, QDesktopWidget, QDialog, QDialogButtonBox, QDoubleSpinBox,
        QFileDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout, QGroupBox, QHBoxLayout,
        QInputDialog, QLabel, QLayout, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton,
        QScrollArea, QSpinBox, QSizePolicy, QSpacerItem, QStyle, QTabWidget, QTextEdit, QVBoxLayout,
        QWidget)
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
from options import (ALL_MODES, NORMAL_FLAGS, MAKEOVER_MODIFIER_FLAGS, Flag, Options_, activate_from_string,
                     get_makeover_groups, get_mode)
from randomizer import randomize

if sys.version_info[0] < 3:
    raise Exception('Python 3 or a more recent version is required. '
                    'Report this to https://github.com/FF6BeyondChaos/BeyondChaosRandomizer/issues')

control_fixed_width = 70
control_fixed_height = 20
spacer_fixed_height = 5
current_theme = config.get('Settings', 'gui_theme', fallback='Light')

# Light mode themes, for items that cannot be styled with the css file due to PyQt limitations
inactive_flag_light_theme_stylesheet = 'background-color: white; border: none; color: black;'
active_flag_light_theme_stylesheet = 'background-color: #CCE4F7; border: 1px solid darkblue; color: black;'
disabled_flag_light_theme_stylesheet = 'background-color: #fedada; border: none; color: black;'
hyperlink_light_theme_stylesheet = 'color: #0d7eb9;'
disabled_flag_text_light_theme_stylesheet = 'color: #c30010;'

# Other mode themes, for items that cannot be styled with the css file due to PyQt limitations
inactive_flag_other_theme_stylesheet = 'background-color: #232629; border: none; color: white;'
active_flag_other_theme_stylesheet = 'background-color: #010030; border: 1px solid #A1A0D0; color: white;'
disabled_flag_other_theme_stylesheet = 'background-color: #390000; border: none; color: white;'
hyperlink_other_theme_stylesheet = 'color: #5dcef9;'
disabled_flag_text_other_theme_stylesheet = 'color: #ee6b6e;'


class QDialogScroll(QDialog):
    def __init__(self, scroll_contents: QWidget, title: str = '', header: str = '',
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

        scroll_area = QScrollArea(self)
        scroll_area.setMinimumWidth(self.minimumWidth() - 100)
        scroll_area.setEnabled(True)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_contents)

        grid_layout.addWidget(header_text, 1, 0, 1, 9)
        grid_layout.addWidget(scroll_area, 2, 0, 1, 9)

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
        self.grid_size_box.setProperty('class', 'dark_background')
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
        self.num_cards_box.setProperty('class', 'dark_background')
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


def handle_conflicts_and_requirements():
    """
    Many flags have conflicts and requirements. Conflicts are two or more flags that cannot be activated together.
    Requirements are flags that must be active, sometimes at a specific value, for a flag to become enabled.

    Whenever any flag value is changed, we need to run through every flag to see if any other flags need to be
        disabled or enabled.

    Flags can be disabled because a requirement is no longer met or because a flag was activated that conflicts
        with it.

    Flags can be enabled because requirements are met or a flag that conflicts with it was deactivated.

    Returns:
        None
    """
    if current_theme == 'Light':
        error_style = disabled_flag_text_light_theme_stylesheet
    else:
        error_style = disabled_flag_text_other_theme_stylesheet

    mode_requirements = []
    mode_conflicts = []
    if Options_.mode:
        mode_requirements = Options_.mode.forced_flags
        mode_conflicts = Options_.mode.prohibited_flags

    for flag in NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS:
        disabled_text = ''
        disabled_value_override = ''

        if flag.name in mode_requirements:
            # If the mode forced_flags is ever changed to support non-boolean flags, this disabled_value_override
            #   will need to be updated to work with any flag value.
            disabled_value_override = True
            if not disabled_text:
                disabled_text = ('<div style="' +
                                 error_style +
                                 '">Flag disabled because:<ul style="margin: 0;"><li>' +
                                 'The flag is required to be used with the selected game mode.</li>')
            else:
                disabled_text += '<li>The flag is required to be used with the selected game mode.</li>'
            pass

        # An if/else is used here so that, if a flag conflicts with the currently selected game mode, only that
        #   conflict will be displayed as a reason the flag is disabled. Listing all of the other normal
        #   conflicts and requirements would only serve to clutter the UI.
        elif flag.name in mode_conflicts:
            if not disabled_text:
                disabled_text = ('<div style="' +
                                 error_style +
                                 '">Flag disabled because:<ul style="margin: 0;"><li>' +
                                 'The flag cannot be used with the selected game mode.</li>')
            else:
                disabled_text += '<li>The flag cannot be used with the selected game mode.</li>'

        else:
            if flag.conflicts:
                conflicting_flags = []
                for conflicting_flag in flag.conflicts:
                    if not Options_.get_flag(conflicting_flag).value == '':
                        conflicting_flags.append(conflicting_flag)
                if conflicting_flags:
                    if not disabled_text:
                        disabled_text = ('<div style="' +
                                         error_style +
                                         '">Flag disabled because:<ul style="margin: 0;"><li>' +
                                         'It conflicts with the following '
                                         + 'active flags: "' + '" and "'.join(conflicting_flags) + '"</li>')
                    else:
                        disabled_text += ('<li>' +
                                          'It conflicts with the following '
                                          + 'active flags: "' + '" and "'.join(conflicting_flags) + '"</li>')

            if flag.requirements:
                requirements_met = get_missing_requirements(flag)

                if not requirements_met:
                    if not disabled_text:
                        disabled_text = ('<div style="' +
                                         error_style +
                                         '">Flag disabled because:<ul style="margin: 0;"><li>' +
                                         flag.get_requirement_string() + '</li>')
                    else:
                        disabled_text += '<li>' + flag.get_requirement_string() + '</li>'

        if disabled_text:
            flag.value = disabled_value_override
            flag_control = flag.controls['input']

            if flag.input_type in ['float2', 'integer']:
                # Block signals to prevent setValue from causing flag_button_clicked from being called
                flag_control.blockSignals(True)
                flag_control.setValue(flag_control.default)
                flag_control.blockSignals(False)
            elif flag.input_type == 'combobox':
                flag_control.setCurrentIndex(max(0, flag.default_index))
            else:
                if disabled_value_override:
                    flag_control.setText('Yes')
                else:
                    flag_control.setText('No')
                flag_control.setChecked(not disabled_value_override == '')
            flag_control.setDisabled(True)
            flag.controls['description'].setText(disabled_text + '</ul></div>' + flag.long_description)

            if current_theme == 'Light':
                flag_control.setStyleSheet(disabled_flag_light_theme_stylesheet)
            else:
                flag_control.setStyleSheet(disabled_flag_other_theme_stylesheet)
        else:
            # Enable control if necessary
            if not flag.controls['input'].isEnabled():
                flag.controls['input'].setDisabled(False)
                if current_theme == 'Light':
                    flag.controls['input'].setStyleSheet(inactive_flag_light_theme_stylesheet)
                else:
                    flag.controls['input'].setStyleSheet(inactive_flag_other_theme_stylesheet)
                flag.controls['description'].setText(flag.long_description)


def get_missing_requirements(flag: Flag, current_index: int = 0) -> str | bool:
    """
    Takes a flag and analyzes it's requirements to see if the requirements are met.

    For the original method call (as indicated by current_index == 0, the method returns a boolean
        indicating whether or not all requirements are met.

    This method also calls itself recursively for each item in the Flag's requirements. These recursive
        calls return True or False depending on whether or not the requirements were met for that part of
        the requirements.
    Returns:
        str
        bool
    """
    requirements = flag.requirements

    if not requirements:
        return True

    if len(requirements) <= current_index:
        return False

    result = True
    for required_flag, required_value in requirements[current_index].items():
        required_flag_object = Options_.get_flag(required_flag)
        if str(required_value) == '*' and not required_flag_object.value == '':
            continue
        if str(required_flag_object.value) == str(required_value):
            continue
        result = False
        break

    return result or get_missing_requirements(flag, current_index + 1)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        # region geometry_data
        self.setWindowTitle('Beyond Chaos Randomizer ' + VERSION)
        screen_size = QDesktopWidget().screenGeometry(-1)
        self.width = int(min(screen_size.width() / 2, 1000))
        self.height = int(screen_size.height() * .8)
        self.left = int(screen_size.width() / 2 - self.width / 2)
        self.top = int(screen_size.height() / 2 - self.height / 2)
        self.setGeometry(self.left, self.top, self.width, self.height)
        # endregion geometry_data

        # values to be sent to Randomizer
        self.version = 'CE-6.1.1'
        self.bingo_type = []
        self.bingo_size = 5
        self.bingo_diff = ''
        self.bingo_cards = 1

        # dictionaries to hold flag data

        # keep a list of all checkboxes
        self.conflicts = {}
        self.requirements = {}

        # dictionary of game presets from drop down
        self.game_presets = SUPPORTED_PRESETS

        # tabs: Flags, Sprites, Battle, etc...
        self.central_widget = QWidget()
        self.tablist = []

        # Load previous flag string
        activate_from_string(flag_string=config.get(
            'Settings',
            'default_flagstring',
            fallback='b c d e f g h i m n o p q r s t w y z '
                     'alphalores improvedpartygear '
                     'informativemiss magicnumbers mpparty '
                     'nicerpoison questionablecontent '
                     'regionofdoom tastetherainbow makeover '
                     'partyparty alasdraco capslockoff '
                     'johnnydmad dancelessons lessfanatical '
                     'swdtechspeed:faster shadowstays'
            ),
            append=False
        )

        # region MenuBar
        file_menu = QMenu('File', self)
        file_menu.addAction('Quit', App.quit)
        self.menuBar().addMenu(file_menu)

        menu_separator = self.menuBar().addMenu('|')
        menu_separator.setProperty('class', 'menu_separator')
        menu_separator.setEnabled(False)

        if not BETA and update.list_available_updates(refresh=False):
            self.menuBar().addAction('Update Available', update_bc)
        else:
            self.menuBar().addAction('Check for Updates', update_bc)

        menu_separator2 = self.menuBar().addMenu('|')
        menu_separator2.setProperty('class', 'menu_separator')
        menu_separator2.setEnabled(False)

        self.menuBar().addAction('Toggle Dark Mode', self.toggle_palette)
        # endregion MenuBar

        vbox = QVBoxLayout()  # Main content container

        # region Layout

        # region Row 1: Title
        title_label = QLabel('Beyond Chaos Randomizer')
        font = QtGui.QFont('Arial', 24, QtGui.QFont.Black)
        title_label.setFont(font)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setMargin(10)
        vbox.addWidget(title_label)
        # endregion Row 1: Title

        # region Row 2: Input and Output
        group_layout = QGroupBox('Input and Output')

        grid_layout = QGridLayout()

        # ROM INPUT
        label_rom_input = QLabel('ROM File:')
        label_rom_input.setAlignment(QtCore.Qt.AlignRight |
                                     QtCore.Qt.AlignVCenter)
        grid_layout.addWidget(label_rom_input, 1, 1)

        self.rom_input = QLineEdit()
        self.rom_input.setText(config.get('Settings', 'input_path', fallback=''))
        self.rom_input.setPlaceholderText('Required')
        self.rom_input.setReadOnly(True)
        grid_layout.addWidget(self.rom_input, 1, 2, 1, 3)

        self.label_rom_error = QLabel()
        self.label_rom_error.setProperty('class', 'error')
        self.label_rom_error.setHidden(True)
        grid_layout.addWidget(self.label_rom_error, 2, 2, 1, 3)

        btn_rom_input = QPushButton('Browse')
        btn_rom_input.setMaximumWidth(self.width)
        btn_rom_input.setMaximumHeight(self.height)
        btn_rom_input.setProperty('class', 'rom_file_picker')
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
        self.rom_output.setText(config.get('Settings', 'output_path', fallback=''))
        self.rom_input.textChanged[str].connect(self.validate_input_rom)
        grid_layout.addWidget(self.rom_output, 3, 2, 1, 3)

        btn_rom_output = QPushButton('Browse')
        btn_rom_output.setMaximumWidth(self.width)
        btn_rom_output.setMaximumHeight(self.height)
        btn_rom_output.setProperty('class', 'rom_output_picker')
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
        self.seed_count.setProperty('class', 'batch_count')
        self.seed_count.setValue(1)
        self.seed_count.setMinimum(1)
        self.seed_count.setMaximum(99)
        self.seed_count.setFixedWidth(50)
        grid_layout.addWidget(self.seed_count, 4, 4)

        btn_generate = QPushButton('Generate')
        btn_generate.setMinimumWidth(125)
        btn_generate.setMaximumWidth(self.width)
        btn_generate.setMaximumHeight(self.height)
        btn_generate.setProperty('class', 'generate_button')
        btn_generate.clicked.connect(lambda: self.generate_seed())
        btn_generate.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        btn_generate_style = QGraphicsDropShadowEffect()
        btn_generate_style.setBlurRadius(3)
        btn_generate_style.setOffset(3, 3)
        btn_generate.setGraphicsEffect(btn_generate_style)
        grid_layout.addWidget(btn_generate, 4, 5)

        group_layout.setLayout(grid_layout)
        vbox.addWidget(group_layout)
        # endregion Row 2: Input and Output

        # region Row 3: Modes and Presets
        group_mode_and_preset = QGroupBox()
        layout_mode_and_preset = QGridLayout()

        # ---- Game Mode Drop Down ---- #
        label_game_mode = QLabel('Game Mode:')
        label_game_mode.setProperty('class', 'game_mode_label')
        layout_mode_and_preset.addWidget(label_game_mode, 1, 1)
        self.mode_box = QComboBox()
        for mode in ALL_MODES:
            self.mode_box.addItem(mode.display_name)
        layout_mode_and_preset.addWidget(self.mode_box, 1, 2)
        self.mode_box.currentTextChanged.connect(
            lambda: self.game_mode_changed()
        )

        # ---- Preset Flags Drop Down ---- #
        label_preset_mode = QLabel('Preset Flags:')
        label_preset_mode.setProperty('class', 'preset_label')
        layout_mode_and_preset.addWidget(label_preset_mode, 1, 3)
        self.preset_box = QComboBox()
        self.preset_box.addItem('Select a flag set')
        self.load_saved_flags()
        for key in self.game_presets.keys():
            self.preset_box.addItem(key)

        self.preset_box.currentTextChanged.connect(
            lambda: self.update_preset_dropdown()
        )
        layout_mode_and_preset.addWidget(self.preset_box, 1, 4)

        label_flag_description = QLabel('Preset Description:')
        label_flag_description.setProperty('class', 'preset_description')
        layout_mode_and_preset.addWidget(label_flag_description, 1, 5)
        self.flag_description = QLabel('Pick a Flag Set!')
        self.flag_description.setProperty('class', 'current_preset')
        layout_mode_and_preset.addWidget(self.flag_description, 1, 6)

        layout_mode_and_preset.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        group_mode_and_preset.setLayout(layout_mode_and_preset)
        group_mode_and_preset.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        vbox.addWidget(group_mode_and_preset)
        # endregion Row 3: Modes and Presets

        # region Row 4: Flags and Flagstring
        group_box_two = QGroupBox()
        middle_h_box = QHBoxLayout()
        middle_right_group_box = QGroupBox('Flag Selection')
        layout_tab_v_box = QVBoxLayout()
        tabs = QTabWidget()
        tabs.setElideMode(True)  # Tabs shrink in size to fit all tabs on screen

        tab_contents = {}
        get_makeover_groups()

        for flag in NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS:
            category = flag.category.replace('_', ' ').title()
            try:
                tab_contents[category].append(flag)
            except KeyError:
                tab_contents[category] = [flag]
                # Force Sprite Categories to be after Sprites
                if category == 'Sprites':
                    tab_contents['Sprite Categories'] = []

        # Remove empty tabs, just in case
        empty_tabs = []
        for tab, flags in tab_contents.items():
            if not flags:
                empty_tabs.append(tab)
        for tab in empty_tabs:
            print(str(tab))
            tab_contents.pop(tab)

        for index, (tab_name, tab_flags) in enumerate(tab_contents.items()):
            if len(tab_flags) > 0:
                tab_layout = QGridLayout()
                flag_count = 0
                current_row = 0
                tab_layout.setColumnStretch(4, 1)  # Long description should use as much space as possible
                tab_layout.setVerticalSpacing(0)

                for flag in tab_flags:
                    # Add spacing above the flag
                    margin_top = QSpacerItem(0, spacer_fixed_height)
                    tab_layout.addItem(margin_top, current_row, 0)
                    current_row += 1

                    if flag.input_type == 'float2':
                        flag_control = QDoubleSpinBox()
                        flag_control.setMinimum(float(flag.minimum_value))
                        flag_control.default = float(flag.default_value)
                        flag_control.setMaximum(float(flag.maximum_value))
                        flag_control.setSingleStep(.1)
                        flag_control.setValue(flag_control.default)
                        flag_control.text = flag.name
                        flag_control.setFixedWidth(control_fixed_width)
                        flag_control.setMinimumHeight(0)
                        flag_control.setFixedHeight(control_fixed_height)
                        flag_label = QLabel(f'{flag.name}')

                        if flag.special_value_text:
                            flag_control.setSpecialValueText(flag.special_value_text)

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
                        flag_control.text = flag.name
                        flag_label = QLabel(f'{flag.name}')

                        if flag.special_value_text:
                            flag_control.setSpecialValueText(flag.special_value_text)

                        flag_control.valueChanged.connect(lambda: self.flag_button_clicked())
                        flag_count += 1
                    elif flag.input_type == 'combobox':
                        flag_control = QComboBox()
                        flag_control.addItems(flag.choices)
                        flag_control.text = flag.name
                        flag_control.setFixedWidth(control_fixed_width)
                        flag_control.setMinimumHeight(0)
                        flag_control.setFixedHeight(control_fixed_height)
                        flag_control.setCurrentIndex(max(0, flag.default_index))

                        if MAKEOVER_MODIFIER_FLAGS and flag.name in MAKEOVER_MODIFIER_FLAGS:
                            flag_label = QLabel(f'{flag.name} (' + str(MAKEOVER_MODIFIER_FLAGS[flag.name]) +
                                                ')')
                        else:
                            flag_label = QLabel(f'{flag.name}')

                        flag_control.activated[str].connect(lambda: self.flag_button_clicked())
                        flag_count += 1
                    else:
                        # Assume boolean
                        flag_control = QPushButton('No')
                        flag_control.setProperty('class', 'flag_control')
                        flag_control.setFixedWidth(control_fixed_width)
                        flag_control.setMinimumHeight(0)
                        flag_control.setFixedHeight(control_fixed_height)
                        flag_control.setCheckable(True)
                        flag_control.value = flag.name
                        flag_label = QLabel(f'{flag.name}')

                        if (flag.name == 'remonsterate' and not len(check_remonsterate()) == 0) or \
                                (flag.name == 'makeover' and not len(check_player_sprites()) == 0):
                            flag_control.setEnabled(False)

                        flag_control.clicked.connect(lambda checked: self.flag_button_clicked())
                        flag_count += 1

                    flag_description = QLabel(f'{flag.long_description}')
                    flag_description.setWordWrap(True)

                    # Connect the flag and controls to each other, allowing for easier actions later
                    flag_control.flag = flag
                    flag.controls = {'input': flag_control, 'label': flag_label, 'description': flag_description}

                    # Add the flag information to the tab
                    tab_layout.addWidget(flag_control, current_row, 1)
                    tab_layout.addWidget(flag_label, current_row, 2)
                    tab_layout.addWidget(flag_description, current_row, 4)
                    current_row += 1

                    # Add spacing below the flag
                    margin_bottom = QSpacerItem(0, spacer_fixed_height)
                    tab_layout.addItem(margin_bottom, current_row, 0)
                    current_row += 1

                    # Add the margins to the flag object so they can be referenced later for changing
                    flag.margins = [margin_top, margin_bottom]

                    h_spacer = QFrame()
                    h_spacer.setFrameShape(QFrame.HLine)
                    h_spacer.setFrameShadow(QFrame.Sunken)
                    if not flag_count == len(tab_flags):
                        h_spacer.setFixedHeight(2)
                        h_spacer.setProperty('class', 'flag_h_spacer')
                        tab_layout.addWidget(h_spacer, current_row, 0, 1, 6)
                        current_row += 1
                    else:
                        # Fake row set to stretch as much as possible. Keeps other rows from stretching.
                        h_spacer.setProperty('class', 'flag_h_spacer_final')
                        tab_layout.addWidget(h_spacer, current_row, 0, 1, 6)
                        tab_layout.setRowStretch(current_row, 1)
                        current_row += 1

                    v_spacer = QFrame()
                    v_spacer.setFrameShape(QFrame.VLine)
                    v_spacer.setFrameShadow(QFrame.Sunken)
                    v_spacer.setFixedWidth(5)
                    v_spacer.setProperty('class', 'flag_v_spacer')
                    tab_layout.addWidget(v_spacer, 0, 3, flag_count * 4 - 1, 1)

                tab = QWidget()
                tab.setLayout(tab_layout)
                self.tablist.append(tab)

                tab_obj = QScrollArea()
                tabs.addTab(tab_obj, tab_name)
                tab_obj.setWidgetResizable(True)
                tab_obj.setWidget(tab)

        layout_tab_v_box.addWidget(tabs)
        self.update_control()

        # This is the line in the layout that displays the string
        # of selected flags and the button to save those flags
        widget_v = QWidget()
        widget_v_box_layout = QVBoxLayout()
        widget_v.setLayout(widget_v_box_layout)

        widget_v_box_layout.addWidget(QLabel('Text-string of selected flags:'))
        self.flag_string = QLineEdit()
        self.flag_string.setText(Options_.get_flag_string())
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
        btn_clear_ui.setProperty('class', 'clear_ui')
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
        vbox.addWidget(group_box_two)
        # endregion Row 4: Flags and Flagstring

        # endregion Layout

        self.central_widget.setLayout(vbox)
        self.setCentralWidget(self.central_widget)
        self.set_palette()
        self.show()

    # ---------------------------------------------------------------
    # ------------ NO MORE LAYOUT DESIGN PAST THIS POINT-------------
    # ---------------------------------------------------------------
    def toggle_palette(self):
        if config.get('Settings', 'gui_theme', fallback='Light') == 'Light':
            self.set_palette('Dark')
        else:
            self.set_palette('Light')

    @staticmethod
    def set_palette(style=None):
        if not style:
            style = config.get('Settings', 'gui_theme', fallback='Light')

        if style == 'Light':
            if not os.path.exists('custom/gui_themes/lightmode.css'):
                print('Error: No lightmode.css file found. App style cannot be changed.')
                return
            with open('custom/gui_themes/lightmode.css', 'r') as f:
                App.setStyleSheet(f.read())

            # Refresh the styles of all controls
            for flag in NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS:
                if flag.controls:
                    flag_control = flag.controls['input']
                    if not flag_control.isEnabled():
                        flag_control.setStyleSheet(disabled_flag_light_theme_stylesheet)
                    else:
                        if not flag.value == '' or flag.always_on:
                            flag.controls['input'].setStyleSheet(active_flag_light_theme_stylesheet)
                        else:
                            flag.controls['input'].setStyleSheet(inactive_flag_light_theme_stylesheet)

        elif style == 'Dark':
            if not os.path.exists('custom/gui_themes/darkmode.css'):
                print('Error: No lightmode.css file found. App style cannot be changed.')
                return
            with open('custom/gui_themes/darkmode.css', 'r') as f:
                App.setStyleSheet(f.read())

            # Refresh the styles of all controls
            for flag in NORMAL_FLAGS + MAKEOVER_MODIFIER_FLAGS:
                if flag.controls:
                    flag_control = flag.controls['input']
                    if not flag_control.isEnabled():
                        flag_control.setStyleSheet(disabled_flag_other_theme_stylesheet)
                    else:
                        if not flag.value == '' or flag.always_on:
                            flag.controls['input'].setStyleSheet(active_flag_other_theme_stylesheet)
                        else:
                            flag.controls['input'].setStyleSheet(inactive_flag_other_theme_stylesheet)

        global current_theme
        current_theme = style
        set_config_value('Settings', 'gui_theme', style)
        handle_conflicts_and_requirements()

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
                    self.flag_string.text().strip() + '|' + self.mode_box.currentText()
            )
            write_flags(
                text,
                (self.flag_string.text().strip() + '|' + self.mode_box.currentText())
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

    def game_mode_changed(self):
        Options_.mode = get_mode(self.sender().currentText())
        handle_conflicts_and_requirements()
        self.flag_string.setText(Options_.get_flag_string())

    def update_preset_dropdown(self):
        text = self.preset_box.currentText()
        index = self.preset_box.findText(text)
        flags = self.game_presets.get(text)
        if index == 0:
            self.clear_ui()
            flags = ''
            self.flag_description.setText('Pick a flag set!')
        elif index == 1:
            self.flag_description.setText('Flags designed for a new player')
            self.mode_box.setCurrentIndex(0)
        elif index == 2:
            self.flag_description.setText(
                'Flags designed for an intermediate player'
            )
            self.mode_box.setCurrentIndex(0)
        elif index == 3:
            self.flag_description.setText(
                'Flags designed for an advanced player'
            )
            self.mode_box.setCurrentIndex(0)
        elif index == 4:
            self.flag_description.setText(
                'Flags designed for a chaotic player'
            )
            self.mode_box.setCurrentIndex(0)
        elif index == 5:
            self.flag_description.setText(
                'Flags designed for KaN easy difficulty races'
            )
            self.mode_box.setCurrentIndex(1)
        elif index == 6:
            self.flag_description.setText(
                'Flags designed for KaN medium difficulty races'
            )
            self.mode_box.setCurrentIndex(1)
        elif index == 7:
            self.flag_description.setText(
                'Flags designed for KaN insane difficulty races'
            )
            self.mode_box.setCurrentIndex(1)
        else:
            mode = flags.split('|')[1]
            flags = flags.split('|')[0]
            self.flag_description.setText('Custom saved flags')
            mode_object = get_mode(mode)
            if mode_object:
                self.mode_box.setCurrentIndex(
                    self.mode_box.findText(mode_object.display_name)
                )
            else:
                self.mode_box.setCurrentIndex(0)
        activate_from_string(flag_string=flags, append=False)
        self.flag_string.setText(flags)
        self.update_control()

    def clear_ui(self):
        self.seed_input.setText('')
        self.mode_box.setCurrentIndex(0)
        self.preset_box.setCurrentIndex(0)
        activate_from_string(flag_string='', append=False)
        self.flag_string.setText(Options_.get_flag_string())
        self.update_control()

    def handle_children(self, flag):
        """
        For a parent flag with a specified value, check to see if the flag has any children. The children are
            contained in a dict object containing the child's name and the value the parent should be set to
            for the child to be visible.

        For each child where the parent is the correct value to make it visible, make the child visible.

        For each child where the parent is NOT the correct value to make it visible, turn the flag off by
            setting it to its default value in addition to making the child invisible.

        Returns:
            None
        """
        for flag_name, required_parent_value in flag.children.items():
            flag_object = Options_.get_flag(flag_name)
            if flag.value == str(required_parent_value):
                if not flag_object.value:
                    flag_object.value = flag_object.default_value.lower()

                # Change spacers before revealing the flag, otherwise they will not display properly
                for spacer in flag_object.margins:
                    spacer.changeSize(0, spacer_fixed_height)

                for control in flag_object.controls.values():
                    # Make all controls visible
                    control.setVisible(True)

            else:
                # Set controls to default value (turn off flag)
                flag_object.value = ''

                for spacer in flag_object.margins:
                    spacer.changeSize(0, 0)

                # Make all controls invisible
                for control in flag_object.controls.values():
                    control.setVisible(False)

            self.update_control([flag_object.controls['input']])

    def update_control(self, controls: [QWidget] = None):
        if not controls:
            controls = []
            for tab in self.tablist:
                controls.extend([c for c in tab.children() if
                                 type(c) in (QPushButton, QSpinBox, QDoubleSpinBox, QComboBox)])

        for control in controls:
            if isinstance(control, QPushButton):
                if not control.flag.value == '':
                    control.setText('Yes')
                else:
                    control.setText('No')

            elif isinstance(control, QSpinBox):
                # Block signals to prevent setValue from causing flag_value_changed from being called
                control.blockSignals(True)
                if not control.flag.value == '':
                    try:
                        control.setValue(int(control.flag.value))
                    except ValueError:
                        if str(control.flag.value).lower() == control.flag.special_value_text.lower():
                            control.setValue(control.minimum())
                else:
                    control.setValue(int(control.flag.default_value))
                control.blockSignals(False)
            elif isinstance(control, QDoubleSpinBox):
                # Block signals to prevent setValue from causing flag_value_changed from being called
                control.blockSignals(True)
                if not control.flag.value == '':
                    try:
                        control.setValue(float(control.flag.value))
                    except ValueError:
                        if str(control.flag.value).lower() == control.flag.special_value_text.lower():
                            control.setValue(control.minimum())
                else:
                    control.setValue(float(control.flag.default_value))
                control.blockSignals(False)
            elif isinstance(control, QComboBox):
                if not control.flag.value == '':
                    control.setCurrentIndex([choice.lower() for choice
                                             in control.flag.choices].index(control.flag.value))
                else:
                    control.setCurrentIndex(control.flag.default_index)

            if not control.flag.value == '' or control.flag.always_on:
                if current_theme == 'Light':
                    control.setStyleSheet(active_flag_light_theme_stylesheet)
                else:
                    control.setStyleSheet(active_flag_other_theme_stylesheet)
            else:
                if current_theme == 'Light':
                    control.setStyleSheet(inactive_flag_light_theme_stylesheet)
                else:
                    control.setStyleSheet(inactive_flag_other_theme_stylesheet)

            self.handle_children(control.flag)
        handle_conflicts_and_requirements()

    def flag_button_clicked(self):
        calling_control = self.sender()

        if isinstance(calling_control, QPushButton):
            if not calling_control.flag.value == '':
                calling_control.setText('No')
                calling_control.flag.value = ''
            else:
                calling_control.setText('Yes')
                calling_control.flag.value = 'True'

        elif isinstance(calling_control, QSpinBox):
            value = int(calling_control.value())
            if value == int(calling_control.flag.minimum_value) and calling_control.flag.special_value_text:
                calling_control.flag.value = calling_control.flag.special_value_text.lower()
            elif (not value == int(calling_control.flag.default_value)) or calling_control.flag.always_on:
                calling_control.flag.value = value
            else:
                calling_control.flag.value = ''

            # Special handling to ensure levelcap min <= levelcap max
            if calling_control.flag.name == 'cap_min':
                Options_.get_flag('cap_max').controls['input'].setMinimum(int(value))
            if calling_control.flag.name == 'cap_max':
                Options_.get_flag('cap_min').controls['input'].setMaximum(int(value))

        elif isinstance(calling_control, QDoubleSpinBox):
            # Get value. Round to two decimal places.
            value = round(calling_control.value(), 2)
            if (value == float(calling_control.flag.minimum_value) and
                    calling_control.flag.special_value_text):
                calling_control.flag.value = calling_control.flag.special_value_text.lower()
            elif (not value == float(calling_control.flag.default_value) or
                  calling_control.flag.always_on):
                # When adding value, remove trailing zeroes and trailing periods left after removing trailing zeroes
                calling_control.flag.value = str(value).rstrip('0').rstrip('.')
            else:
                calling_control.flag.value = ''

        elif isinstance(calling_control, QComboBox):
            value = calling_control.currentText()
            if not value == calling_control.flag.default_value or calling_control.flag.always_on:
                calling_control.flag.value = value.lower()
            else:
                calling_control.flag.value = ''

        if calling_control.flag.value != '' or calling_control.flag.always_on:
            if current_theme == 'Light':
                calling_control.setStyleSheet(active_flag_light_theme_stylesheet)
            else:
                calling_control.setStyleSheet(active_flag_other_theme_stylesheet)
        else:
            if current_theme == 'Light':
                calling_control.setStyleSheet(inactive_flag_light_theme_stylesheet)
            else:
                calling_control.setStyleSheet(inactive_flag_other_theme_stylesheet)

        self.handle_children(calling_control.flag)
        handle_conflicts_and_requirements()
        self.flag_string.setText(Options_.get_flag_string())

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

    # Get seed generation parameters from UI to prepare for
    # seed generation. This will show a confirmation dialog,
    # and call the local Randomizer.py file and pass arguments
    # to it
    def generate_seed(self):
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

        if self.rom_input.text() == '':
            QMessageBox.about(
                self,
                'Error',
                'You need to select a FFVI rom!'
            )
        else:
            if not os.path.exists(self.rom_input.text()):
                self.rom_input.setText('')
                QMessageBox.about(
                    self,
                    'Error',
                    f'No ROM was found at the path {str(self.rom_input.text())}. Please choose a different ROM file.'
                )
                return
            try:
                f = open(self.rom_input.text(), 'rb')
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

            display_seed = self.seed_input.text()

            flags = Options_.get_flag_string()
            current_mode = get_mode(self.mode_box.currentText()).name

            flag_scroll_contents = ''
            for flag in flags.split(' '):
                if len(flag) == 1:
                    flag_scroll_contents += flag + ' '
                else:
                    flag_scroll_contents += '\n' + flag

            if self.seed_input.text() == '':
                display_seed = '(none)'
            if flags == '':
                QMessageBox.about(
                    self,
                    'Error',
                    'You need to select a flag!'
                )
                return

            if 'bingoboingo' in flags:
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
                    'Rom:', self.rom_input.text(),
                    'Output:', self.rom_output_directory,
                    'Seed:', display_seed,
                    'Batch:', self.seed_count.text(),
                    'Mode:', current_mode,
                    'Flags:')
            )
            flag_message = QLabel(flag_scroll_contents)
            flag_message.setProperty('class', 'flag_message')
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
                seed = self.seed_input.text() or int(time.time())
                seeds_to_generate = int(self.seed_count.text())
                result_files = []
                for currentSeed in range(seeds_to_generate):
                    print('Rolling seed ' + str(currentSeed + 1) + ' of ' + str(seeds_to_generate) + '.')
                    # User selects confirm/accept/yes option
                    bundle = f'{self.version}|{current_mode}|{flags}|{seed}'
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
                            'infile_rom_path': self.rom_input.text(),
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
                        if '.' in self.rom_input.text():
                            temp_name = os.path.basename(self.rom_input.text()).rsplit('.', 1)
                        else:
                            temp_name = [os.path.basename(self.rom_input.text()), 'smc']
                        seed = bundle.split('|')[-1]
                        result_file = os.path.join(self.rom_output_directory,
                                                   '.'.join([os.path.basename(temp_name[0]),
                                                             str(seed), temp_name[1]]))
                        if seed:
                            seed = str(int(seed) + 1)
                    except Exception as gen_exception:
                        traceback.print_exc()
                        gen_traceback = QTextEdit(
                            '<br>'.join(traceback.format_exc().splitlines())
                        )
                        gen_traceback.setProperty('class', 'traceback')
                        gen_traceback.setReadOnly(True)
                        if current_theme == 'Light':
                            hyperlink_style = hyperlink_light_theme_stylesheet
                        else:
                            hyperlink_style = hyperlink_other_theme_stylesheet
                        QDialogScroll(
                            title=f'Exception: {str(type(gen_exception).__name__)}',
                            header=f'A {str(type(gen_exception).__name__)} ' +
                                   'exception occurred '
                                   'that prevented randomization: ' +
                                   '<br>' +
                                   '<br>' +
                                   'Please submit the following traceback over at the '
                                   f'<a style="{hyperlink_style}" ' +
                                   'href="https://discord.gg/ZCHZp7qxws">Beyond Chaos Barracks discord</a> '
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
    QApplication.setStyle('fusion')
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
