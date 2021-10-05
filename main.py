

import typing
import os
import sys
import asyncio


from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWebEngineCore import *
from PyQt5.QtWebEngine import *
from PyQt5.QtPrintSupport import *
import PyQt5.QtNetwork as network
from qasync import QEventLoop

import gc
import psutil
from adblockparser import AdblockRules

with open("./easylist.txt", 'r', encoding="utf8") as f:
    raw_rules = f.readlines()
    rules = AdblockRules(raw_rules)



class WebEngineUrlRequestInterceptor(QWebEngineUrlRequestInterceptor):
  def interceptRequest(self, info):
    url = info.requestUrl().toString()
    if rules.should_block(url):
      print("block::::::::::::::::::::::", url)
      info.block(True)





def set_transparent(target: QMainWindow, opacity=0.3):
  target.setWindowOpacity(opacity)
  target.setAttribute(Qt.WA_TranslucentBackground, True)



class AmashiWebEngineView(QWebEngineView):
  def __init__(self, parent: typing.Optional[QWidget]) -> None:
    super(AmashiWebEngineView, self).__init__(parent=parent)





  def update_transparency(self):
    self.setStyleSheet("background: rgba(0, 0, 0, 0.9); ")



class AmashiTabWidget(QTabWidget):
  def __init__(self, parent):
    super(AmashiTabWidget, self).__init__(parent=parent)

    self.setDocumentMode(True)
    self.setTabsClosable(True)


class AmashiToolBar(QToolBar):
  def __init__(self, parent, name):
    super(AmashiToolBar, self).__init__(name, parent)

    back_btn = QAction("Back", self)

    back_btn.setStatusTip("Back to previous page")

    back_btn.triggered.connect(lambda: self.parent().tabs.currentWidget().back())

    self.addAction(back_btn)

    next_btn = QAction("Forward", self)
    next_btn.setStatusTip("Forward to next page")
    next_btn.triggered.connect(lambda: self.parent().tabs.currentWidget().forward())
    self.addAction(next_btn)

    reload_btn = QAction("Reload", self.parent())
    reload_btn.setStatusTip("Reload page")
    reload_btn.triggered.connect(lambda: self.parent().tabs.currentWidget().reload())
    self.addAction(reload_btn)

    home_btn = QAction("Home", self.parent())
    home_btn.setStatusTip("Go home")

    home_btn.triggered.connect(self.parent().navigate_home)
    self.addAction(home_btn)

    self.addSeparator()

    self.urlbar = QLineEdit()

    self.urlbar.returnPressed.connect(self.parent().navigate_to_url)
    self.addWidget(self.urlbar)

    stop_btn = QAction("Stop", self.parent())
    stop_btn.setStatusTip("Stop loading current page")
    stop_btn.triggered.connect(lambda: self.parent().tabs.currentWidget().stop())
    self.addAction(stop_btn)


class AmashiOpacitySlider(QSlider):
  def __init__(self, main, bar):
    super(AmashiOpacitySlider, self).__init__(parent=bar)
    self.main: AmashiMainWindow = main

    self.setMinimum(0)
    self.setMaximum(10)

    self.setOrientation(Qt.Horizontal)

  def valueChanged(self, value: int):
    self.main.update_transparency(value * 1.0)



class AmashiStatusBar(QStatusBar):
  def __init__(self, parent):
    super(AmashiStatusBar, self).__init__(parent=parent)
    self.opacity_slider = AmashiOpacitySlider(parent, self)
    self.addWidget(self.opacity_slider)




class AmashiMainWindow(QMainWindow):
  def __init__(self, app):
    super(AmashiMainWindow, self).__init__()
    interceptor = WebEngineUrlRequestInterceptor()
    QWebEngineProfile.defaultProfile().setRequestInterceptor(interceptor)

    self.app = app

    self.loop = QEventLoop(self.app)

    set_transparent(self, 0.5)
    self.setWindowTitle("Amashi")
    self.resize(QSize(1000, 800))
    self.tabs = AmashiTabWidget(self)
    self.setCentralWidget(self.tabs)
    self.show()


    self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)

    self.tabs.currentChanged.connect(self.current_tab_changed)

    self.tabs.tabCloseRequested.connect(self.close_current_tab)



    self.status = QStatusBar()
    set_transparent(self.status, 0.5)

    self.setStatusBar(self.status)

    self.tool_bar = AmashiToolBar(self, "Navigation")
    self.addToolBar(self.tool_bar)

    self.add_new_tab(QUrl('http://www.google.com'), 'Homepage')

  def update_transparency(self, value: float):
    self.setWindowOpacity(value)
    self.status.setWindowOpacity(value)

  def add_new_tab(self, qurl = None, label ="Blank"):
    if qurl is None:
      qurl = QUrl('http://www.google.com')

    browser = AmashiWebEngineView(self)
    browser.setUrl(qurl)
    browser.page().runJavaScript("""
    document.body.style.backgroundColor = "transparent";
    setInterval(() => {
      [...document.querySelectorAll("*")].forEach(v => v.style.backgroundColor = 'transparent');
    }, 5000);
    """)

    i = self.tabs.addTab(browser, label)
    self.tabs.setCurrentIndex(i)

    browser.urlChanged.connect(lambda qurl, browser = browser: self.update_urlbar(qurl, browser))

    browser.loadFinished.connect(lambda _, i = i, browser = browser: self.tabs.setTabText(i, browser.page().title()))

  def tab_open_doubleclick(self, i):
    if i == -1:
      self.add_new_tab()

  def current_tab_changed(self, i):
    qurl = self.tabs.currentWidget().url()

    self.update_urlbar(qurl, self.tabs.currentWidget())

    self.update_title(self.tabs.currentWidget())

  def close_current_tab(self, i):
    if self.tabs.count() < 2:
      return

    self.tabs.removeTab(i)

  def update_title(self, browser):
    if browser != self.tabs.currentWidget():
      return

    title = self.tabs.currentWidget().page().title()
    self.setWindowTitle(title)

  def navigate_home(self):
    self.tabs.currentWidget().setUrl(QUrl("http://www.google.com"))

  # method for navigate to url
  def navigate_to_url(self):
    q = QUrl(self.tool_bar.urlbar.text())

    if q.scheme() == "":
      q.setScheme("http")

    self.tabs.currentWidget().setUrl(q)

  def update_urlbar(self, q, browser = None):
    if browser != self.tabs.currentWidget():
      return

    self.tool_bar.urlbar.setText(q.toString())

    self.tool_bar.urlbar.setCursorPosition(0)
