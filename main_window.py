import subprocess
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QMenuBar, QMenu,
    QHBoxLayout, QVBoxLayout, QWidget, QListWidget, QListWidgetItem,
    QStatusBar, QSplitter, QStackedWidget, QLabel, QPushButton, QSizePolicy, QMessageBox, QFileDialog
)

from PySide6.QtGui import QAction, QIcon, QPixmap, QFont, QPainter
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QSize

import os
import logging

from ui.cadface import ModelingMode
from ui.caeface import SimulationMode
from ui.welcome import WelcomePage

from ui.embedded_exe_widget import EmbeddedExeWidget
from pathlib import Path

# 数据库工具
from ui.knowledge_base.utils.db_connect import DatabaseManager
from ui.knowledge_base.utils.excel_importer import ExcelImporter
from ui.knowledge_base.ui.knowledge_window import KnowledgeBaseWindow
from ui.knowledge_base.ui.database_window import DatabaseWindow
# 模型库查看窗口
from ui.knowledge_base.utils.occ import ViewerWindow_main

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("机床正向设计创新技术平台")
        self.resize(1400, 900)

        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.resources_dir = os.path.join(self.project_root, "resources")
        self.icons_dir = os.path.join(self.resources_dir, "icons")
        self.json_output_dir = os.path.join(self.project_root, "data", "json")

        self.setWindowIcon(self.get_icon("app.png", True))
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.apply_style()

        self.modeling_mode = None
        self.simulation_mode = None
        self.step_viewer = None  # 模型库嵌入页

        self.initialize_actions()
        self.new_action.triggered.connect(self.on_new_action_triggered)

        self.setup_ui()
        self.init_modeling_mode()
        self.init_simulation_mode()
        self.setup_menu()
        self.setup_statusbar()
        self.data_base_status = False

        self.db_manager = DatabaseManager()
        self.excel_importer = ExcelImporter(self.db_manager)

        # === 新增：与仿真下拉面板相关的状态 ===
        self.simulation_dropdown_item = None          # QListWidgetItem (用于承载面板)
        self.simulation_dropdown_widget = None        # QWidget 面板本体
        self.simulation_panel_expanded = False        # 当前是否展开
        self.simulation_panel_signals_connected = False  # 仿真控制面板信号是否已连接
        # === 新增结束 ===

    def initialize_actions(self):
        self.new_action = QAction(self.get_icon("new.png", True), "新建", self)
        self.open_action = QAction(self.get_icon("machine.png", True), "打开", self)
        self.import_action = QAction(self.get_icon("import.png", True), "导入", self)
        self.export_action = QAction(self.get_icon("export.png", True), "导出", self)

    def on_new_action_triggered(self):
        if hasattr(self, "modeling_mode") and self.modeling_mode is not None:
            items = self.sidebar.findItems("结构建模", Qt.MatchExactly)
            if items:
                self.sidebar.setCurrentItem(items[0])
                self.on_sidebar_item_clicked(items[0])
            else:
                self.modeling_mode.activate_modeling_mode()
        else:
            logger.error("建模模块未正确初始化")

    def init_modeling_mode(self):
        self.modeling_mode = ModelingMode(self)
        self.right_container.addWidget(self.modeling_mode.opengl_widget)

    def init_simulation_mode(self):
        self.simulation_mode = SimulationMode(self)
        self.right_container.addWidget(self.simulation_mode.opengl_widget)

    def show_jdr_exe(self):
        exe_path = Path(__file__).resolve().parent.parent / r"ui\external\WinFormsApp1\bin\Debug\net8.0-windows\WinFormsapp.exe"
        exe_path = exe_path.resolve()
        self.jdr_exe_widget = EmbeddedExeWidget(exe_path)
        self.right_container.addWidget(self.jdr_exe_widget)
        self.right_container.setCurrentWidget(self.jdr_exe_widget)

    def show_dt_exe(self):
        exe_path = Path(__file__).resolve().parent.parent / r"ui\external\FUTU\Simdroid\bin\IBE.exe"
        exe_path = exe_path.resolve()
        self.dt_exe_widget = EmbeddedExeWidget(exe_path)
        self.right_container.addWidget(self.dt_exe_widget)  
        self.right_container.setCurrentWidget(self.dt_exe_widget)

    def show_jd_exe(self):
        exe_path = Path(__file__).resolve().parent.parent / r"ui\external\precision\GearErrorApp.exe"
        exe_path = exe_path.resolve()
        subprocess.Popen(str(exe_path), shell=True, creationflags=subprocess.CREATE_NO_WINDOW)

    def apply_style(self):
        css_path = os.path.join(os.path.dirname(__file__), "main_style.qss")
        if os.path.exists(css_path):
            try:
                with open(css_path, "r", encoding="utf-8-sig") as css_file:
                    self.setStyleSheet(css_file.read())
            except Exception as e:
                logger.error(f"加载样式表失败: {e}")
        else:
            logger.warning(f"样式表文件不存在: {css_path}")

    def get_icon(self, icon_name, placeholder=False):
        icon_path = os.path.join(self.icons_dir, icon_name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            logger.warning(f"图标文件不存在: {icon_path}")
            return QIcon()

    def setup_menu(self):
        menu_bar = QMenuBar(self)

        self.new_action = QAction(self.get_icon("new.png", True), "新建", self)
        self.open_action = QAction(self.get_icon("machine.png", True), "打开", self)
        self.import_action = QAction(self.get_icon("import.png", True), "导入", self)
        self.export_action = QAction(self.get_icon("export.png", True), "导出", self)

        file_menu = menu_bar.addMenu("文件")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.export_action)

        help_menu = menu_bar.addMenu("帮助")
        self.manual_action = QAction(self.get_icon("help.png", True), "使用说明", self)
        help_menu.addAction(self.manual_action)
        self.about_action = QAction(self.get_icon("about.png", True), "关于", self)
        self.about_action.setStatusTip("机床正向设计软件V01版本")
        help_menu.addAction(self.about_action)

        self.setMenuBar(menu_bar)

        self.new_action.triggered.connect(self.on_new_action_triggered)
        self.manual_action.triggered.connect(self.show_manual_dialog)

    def show_manual_dialog(self):
        from helpdoc.ManualDialog import ManualDialog
        manual_path = os.path.join(self.project_root, "helpdoc", "manual.md")
        dlg = ManualDialog(manual_path, self)
        dlg.exec()

    def setup_statusbar(self):
        status_bar = self.statusBar()
        status_bar.showMessage(f"就绪 | 侧边栏宽度: {self.sidebar.width()}px")

        custom_widget = QWidget()
        layout = QHBoxLayout(custom_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.data_base_label = QLabel("数据库未连接")
        layout.addWidget(self.data_base_label)
        status_bar.addPermanentWidget(custom_widget)

    def setup_ui(self):
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(0, 0, 0, 5)

        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.setChildrenCollapsible(False)

        self.sidebar = QListWidget()
        self.sidebar.setIconSize(QSize(24, 24))
        sidebar_items = [
            ("数据库", "database.png"),
            ("知识库", "knowledge.png"),
            ("模型库", "model.png"),
            ("结构建模", "modeling.png"),
            ("结构仿真", "simulation.png")
        ]
        for text, icon in sidebar_items:
            self.add_sidebar_item(self.sidebar, text, icon)
        self.sidebar.setMinimumWidth(85)
        self.sidebar.setMaximumWidth(1200)

        # 原本存在的下方面板容器保持不动（不再使用），以确保其它功能不受影响
        self.control_panel_container = QWidget()
        self.control_panel_container.setVisible(False)
        self.control_panel_layout = QVBoxLayout(self.control_panel_container)
        self.control_panel_layout.setContentsMargins(5, 5, 5, 5)

        self.left_splitter.addWidget(self.sidebar)
        self.left_splitter.addWidget(self.control_panel_container)
        self.left_splitter.setSizes([300, 300])
        left_layout.addWidget(self.left_splitter)

        self.horizontal_splitter = QSplitter(Qt.Horizontal)
        self.horizontal_splitter.setChildrenCollapsible(False)
        self.horizontal_splitter.setHandleWidth(5)
        self.horizontal_splitter.addWidget(self.left_container)

        self.right_container = QStackedWidget()  # 右侧界面
        self.right_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.welcome_page = WelcomePage(self)
        self.welcome_page.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.right_container.addWidget(self.welcome_page)

        # 嵌入模型库查看页面
        self.step_viewer = ViewerWindow_main()
        self.right_container.addWidget(self.step_viewer)

        # 嵌入数据库查看页面
        self.database_viewer = DatabaseWindow()
        self.right_container.addWidget(self.database_viewer)

        # 嵌入知识库查看页面
        self.knowledge_viewer = KnowledgeBaseWindow()
        self.right_container.addWidget(self.knowledge_viewer)

        self.right_container.setCurrentWidget(self.welcome_page)

        self.horizontal_splitter.addWidget(self.right_container)
        main_layout.addWidget(self.horizontal_splitter)

        self.sidebar.itemClicked.connect(self.on_sidebar_item_clicked)

        total_width = max(self.width(), 800)
        left_w = 270
        right_w = total_width - left_w
        self.horizontal_splitter.setSizes([left_w, max(1, right_w)])

        self.horizontal_splitter.splitterMoved.connect(self.update_splitter_status)

    def add_sidebar_item(self, list_widget, text, icon_name):
        item = QListWidgetItem(self.get_icon(icon_name), text)
        list_widget.addItem(item)

    def handle_thermal_simulation(self):
        self.show_jdr_exe()

    def handle_MBS_simulation(self):
        self.show_dt_exe()

    def handle_stiff_simulation(self):
        self.show_dt_exe()

    def handle_precise_simulation(self):
        self.show_jd_exe()

    # === 创建或获取仿真下拉面板（位于“结构仿真”项下面） ===
    def ensure_simulation_dropdown_panel(self):
        if self.simulation_dropdown_item is not None:
            return
        # 找到“结构仿真”项的索引
        simulation_items = self.sidebar.findItems("结构仿真", Qt.MatchExactly)
        if not simulation_items:
            logger.error("未找到 '结构仿真' 侧边栏项，无法创建下拉面板")
            return
        sim_item = simulation_items[0]
        sim_row = self.sidebar.row(sim_item)
        # 在其后插入一个新的空白条目
        self.simulation_dropdown_item = QListWidgetItem()
        # 该条目不参与选择
        self.simulation_dropdown_item.setFlags(Qt.NoItemFlags)
        self.sidebar.insertItem(sim_row + 1, self.simulation_dropdown_item)
        # 创建面板容器（使用仿真模块里的控制面板）
        self.simulation_dropdown_widget = QWidget()
        v_layout = QVBoxLayout(self.simulation_dropdown_widget)
        v_layout.setContentsMargins(8, 0, 0, 0)
        v_layout.setSpacing(0)
        panel = self.simulation_mode.cae_control_panel #从 simulation_mode 里取出仿真控制面板对象（CAEControlPanel 实例）
        v_layout.addWidget(panel)#把仿真控制面板 panel 添加到刚才的垂直布局里
        # 只绑定一次信号
        if not self.simulation_panel_signals_connected:
            panel.thermalSimRequested.connect(self.handle_thermal_simulation, type=Qt.UniqueConnection)
            panel.mbsSimRequested.connect(self.handle_MBS_simulation, type=Qt.UniqueConnection)
            panel.stiffnessSimRequested.connect(self.handle_stiff_simulation, type=Qt.UniqueConnection)
            panel.precisionSimRequested.connect(self.handle_precise_simulation, type=Qt.UniqueConnection)
            self.simulation_panel_signals_connected = True
        # 将面板挂到条目上
        self.sidebar.setItemWidget(self.simulation_dropdown_item, self.simulation_dropdown_widget)
        # 初始收起：高度设为 0
        self.simulation_dropdown_item.setSizeHint(QSize(self.sidebar.width(), 0))
        self.simulation_panel_expanded = False

    def toggle_simulation_dropdown(self):
        if self.simulation_dropdown_item is None:
            self.ensure_simulation_dropdown_panel()

        if self.simulation_dropdown_item is None:
            return  # 安全检查

        if self.simulation_panel_expanded:
            # 收起
            self.simulation_dropdown_item.setSizeHint(QSize(self.sidebar.width(), 0))
            self.simulation_panel_expanded = False
            self.statusBar().showMessage("结构仿真面板: 已收起", 2000)
        else:
            # 展开：获取内容的推荐高度
            h = self.simulation_dropdown_widget.sizeHint().height()
            self.simulation_dropdown_item.setSizeHint(QSize(self.sidebar.width(), h))
            self.simulation_panel_expanded = True
            self.statusBar().showMessage("结构仿真面板: 已展开", 2000)

    def collapse_simulation_dropdown_if_needed(self):
        if self.simulation_panel_expanded and self.simulation_dropdown_item is not None:
            self.simulation_dropdown_item.setSizeHint(QSize(self.sidebar.width(), 0))
            self.simulation_panel_expanded = False


    def on_sidebar_item_clicked(self, item):
        item_text = item.text()

        # >>> 如果当前点击的不是“结构建模”，就隐藏建模使用的左侧 control_panel_container
        if item_text != "结构建模" and self.control_panel_container.isVisible():
            self.control_panel_container.setVisible(False)

        if item_text == "结构仿真":
            self.simulation_mode.activate_simulation_mode()# 激活右侧仿真视图
            self.toggle_simulation_dropdown()# 切换下拉面板展开/收起
        else:
            # 切换其它项时收起仿真面板
            self.collapse_simulation_dropdown_if_needed()

            if item_text == "结构建模":
                self.modeling_mode.activate_modeling_mode()
                self.control_panel_container.setVisible(True)
                self.statusBar().showMessage("切换到: 结构建模", 2000)

            elif item_text == "数据库":
                self.right_container.setCurrentWidget(self.database_viewer)
                self.statusBar().showMessage("切换到: 数据库", 2000)

            elif item_text == "知识库":
                self.right_container.setCurrentWidget(self.knowledge_viewer)
                self.statusBar().showMessage("切换到: 知识库", 2000)

            elif item_text == "模型库":
                self.right_container.setCurrentWidget(self.step_viewer)
                self.statusBar().showMessage("切换到: 模型库", 2000)

            else:
                self.right_container.setCurrentIndex(0)
                self.statusBar().showMessage(f"切换到: {item_text} 模式", 2000)

    def update_splitter_status(self, pos, index):
        self.statusBar().showMessage(f"侧边栏宽度: {self.sidebar.width()}px", 2000)