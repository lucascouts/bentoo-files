#!/usr/bin/env python3

import collections
import glob
import urllib.request
import gettext
import gi
import json
import locale
import logging
import os
import subprocess
import sys
import webbrowser

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf


class EmbedManager:
    """manage included applications"""
    def __init__(self, *args):
        self.apps = []
        self.count = 0
        for app in args:
            self.apps.append(app)

    def get_modules(self, window: Gtk.Window):
        for app in self.apps:
            app.load(window)
        self.count = sum((1 for x in self.apps if x.loaded))

    def display(self, window: Gtk.Window):
        for app in self.apps:
            app.display(window)
            if app.loaded:
                btn = window.builder.get_object(app.name)
                if self.count < 2:
                    btn.set_margin_start(200)
                    btn.set_margin_end(200)
                #TODO if self.count>2 !!! ???


class Embed:
    """abstact class for include app"""
    def __init__(self):
        """ abstact class initialisation """
        self.name = "app" + self.__class__.__name__[5:]
        self.loaded = False
        self.box = None

    def load(self, window: Gtk.Window) -> bool:
        """ load modules if installed"""
        raise Exception('abstract method')

    def display(self, window: Gtk.Window):
        """ show btn and add page"""
        window.builder.get_object(self.name).set_visible(self.loaded)
        if self.loaded:
            window.builder.get_object("stack").add_named(self.box, self.name + "page")

class EmbedLayouts(Embed):
    """Gnome layout switcher"""
    def load(self, window: Gtk.Window) -> bool:
        try:
            from layoutswitcherlib.layoutsbox import LayoutBox
            try:
                self.box = LayoutBox(window, usehello=True)
            except Exception as err:
                print("Error in Embled application:", err)
        except ModuleNotFoundError as err:
            print(f"Info: Gnome-layout-switcher not installed")
        self.loaded = self.box is not None
        return self.loaded

class EmbedBrowser(Embed):
    """Application-utility"""
    def load(self, window: Gtk.Window) -> bool:
        try:
            from application_utility.browser.application_browser import ApplicationBrowser
            from application_utility.browser.exceptions import NoAppInIsoError
            from application_utility.config.hello_config import HelloConfig
            try:
                conf = HelloConfig(application="manjaro-hello")
                self.box = ApplicationBrowser(conf, window)
            except Exception as err:
                print("Error in Embled application:", err)
        except ModuleNotFoundError as err:
            print(f"Info: Application-utility not installed")
        self.loaded = self.box is not None
        return self.loaded


class Hello(Gtk.Window):
    """Hello"""

    def __init__(self):
        Gtk.Window.__init__(self, title="Manjaro Hello", border_width=6)
        self.app = "manjaro-hello"
        self.dev = "--dev" in sys.argv  # Dev mode activated ?

        # Load preferences
        if self.dev:
            self.preferences = read_json("data/preferences.json")
            self.preferences["data_path"] = "data/"
            self.preferences["desktop_path"] = os.getcwd() + f"/{self.app}.desktop"
            self.preferences["locale_path"] = "locale/"
            self.preferences["ui_path"] = f"ui/{self.app}.glade"
        else:
            self.preferences = read_json(f"/usr/share/{self.app}/data/preferences.json")
        # Get saved infos
        self.save = read_json(self.preferences["save_path"])
        if not self.save:
            self.save = {"locale": None}

        # Init window
        self.builder = Gtk.Builder.new_from_file(self.preferences["ui_path"])
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("window")

        # Subtitle of headerbar
        self.builder.get_object("headerbar").props.subtitle = ' '.join(get_os_infos())

        # Load images
        if os.path.isfile(self.preferences["logo_path"]):
            logo = GdkPixbuf.Pixbuf.new_from_file(self.preferences["logo_path"])
            self.window.set_icon(logo)
            self.builder.get_object("distriblogo").set_from_pixbuf(logo)
            self.builder.get_object("aboutdialog").set_logo(logo)

        for btn in self.builder.get_object("social").get_children():
            icon_path = self.preferences["data_path"] + "img/" + btn.get_name() + ".png"
            self.builder.get_object(btn.get_name()).set_from_file(icon_path)

        for widget in self.builder.get_object("homepage").get_children():
            if isinstance(widget, Gtk.Button) and \
                    widget.get_image_position() is Gtk.PositionType.RIGHT:
                img = Gtk.Image.new_from_file(
                    self.preferences["data_path"] + "img/external-link.png")
                img.set_margin_start(2)
                widget.set_image(img)

        # Create pages
        self.pages = os.listdir("{}/pages/{}".format(self.preferences["data_path"],
                                                     self.preferences["default_locale"]))
        for page in self.pages:
            scrolled_window = Gtk.ScrolledWindow()
            viewport = Gtk.Viewport(border_width=10)
            label = Gtk.Label(wrap=True)
            viewport.add(label)
            scrolled_window.add(viewport)
            scrolled_window.show_all()
            self.builder.get_object("stack").add_named(scrolled_window, page + "page")

        # Init translation
        self.default_texts = {}
        gettext.bindtextdomain(self.app, self.preferences["locale_path"])
        gettext.textdomain(self.app)
        self.builder.get_object("languages").set_active_id(self.get_best_locale())

        # Set autostart switcher state
        self.autostart = os.path.isfile(fix_path(self.preferences["autostart_path"]))
        self.builder.get_object("autostart").set_active(self.autostart)

        # Live systems
        if os.path.exists(self.preferences["live_path"]) and os.path.isfile(self.preferences["installer_path"]):
            self.builder.get_object("installlabel").set_visible(True)
            self.builder.get_object("install").set_visible(True)
        # Installed systems
        else:
            manager = EmbedManager(EmbedBrowser(), EmbedLayouts())
            manager.get_modules(self)
            manager.display(self)

        self.window.show()

    def get_best_locale(self):
        """Choose best locale, based on user's preferences.
        :return: locale to use
        :rtype: str
        """
        path = self.preferences["locale_path"] + "{}/LC_MESSAGES/" + self.app + ".mo"
        if os.path.isfile(path.format(self.save["locale"])):
            return self.save["locale"]
        elif self.save["locale"] == self.preferences["default_locale"]:
            return self.preferences["default_locale"]
        else:
            sys_locale = locale.getdefaultlocale()[0]
            # If user's locale is supported
            if os.path.isfile(path.format(sys_locale)):
                if "_" in sys_locale:
                    return sys_locale.replace("_", "-")
                else:
                    return sys_locale
            # If two first letters of user's locale is supported (ex: en_US -> en)
            elif os.path.isfile(path.format(sys_locale[:2])):
                return sys_locale[:2]
            else:
                return self.preferences["default_locale"]

    def set_locale(self, use_locale):
        """Set locale of ui and pages.
        :param use_locale: locale to use
        :type use_locale: str
        """
        try:
            translation = gettext.translation(self.app, self.preferences[
                "locale_path"], [use_locale], fallback=True)
            translation.install()
        except OSError:
            return

        self.save["locale"] = use_locale

        # Real-time locale changing

        elts = {
            "comments": {"aboutdialog"},
            "label": {
                "autostartlabel",
                "development",
                "chat",
                "donate",
                "firstcategory",
                "forum",
                "install",
                "installlabel",
                "involved",
                "mailling",
                "readme",
                "release",
                "secondcategory",
                "thirdcategory",
                "welcomelabel",
                "welcometitle",
                "wiki"
            },
            "tooltip_text": {
                "about",
                "home",
                "development",
                "chat",
                "donate",
                "forum",
                "mailling",
                "wiki"
            }
        }
        for method in elts:
            if method not in self.default_texts:
                self.default_texts[method] = {}
            for elt in elts[method]:
                if elt not in self.default_texts[method]:
                    self.default_texts[method][elt] = getattr(
                        self.builder.get_object(elt), "get_" + method)()
                getattr(self.builder.get_object(elt), "set_" + method)(_(self.default_texts[method][elt]))

        # Change content of pages
        for page in self.pages:
            child = self.builder.get_object("stack").get_child_by_name(page + "page")
            label = child.get_children()[0].get_children()[0]
            label.set_markup(self.get_page(page))

    def set_autostart(self, autostart):
        """Set state of autostart.
        :param autostart: wanted autostart state
        :type autostart: bool
        """
        try:
            if autostart and not os.path.isfile(fix_path(self.preferences["autostart_path"])):
                os.symlink(self.preferences["desktop_path"],
                           fix_path(self.preferences["autostart_path"]))
            elif not autostart and os.path.isfile(fix_path(self.preferences["autostart_path"])):
                os.unlink(fix_path(self.preferences["autostart_path"]))
            # Specific to i3
            i3_config = fix_path("~/.i3/config")
            if os.path.isfile(i3_config):
                i3_autostart = "exec --no-startup-id " + self.app
                with open(i3_config, "r+") as file:
                    content = file.read()
                    file.seek(0)
                    if autostart:
                        file.write(content.replace("#" + i3_autostart, i3_autostart))
                    else:
                        file.write(content.replace(i3_autostart, "#" + i3_autostart))
                    file.truncate()
            self.autostart = autostart
        except OSError as error:
            print(error)

    def get_page(self, name):
        """Read page according to language.
        :param name: name of page (filename)
        :type name: str
        :return: text to load
        :rtype: str
        """
        filename = self.preferences["data_path"] + "pages/{}/{}".format(self.save["locale"], name)
        if not os.path.isfile(filename):
            filename = self.preferences["data_path"] + \
                       "pages/{}/{}".format(self.preferences["default_locale"], name)
        try:
            with open(filename, "r") as fil:
                return fil.read()
        except OSError:
            return _("Can't load page.")

    # Handlers
    def on_languages_changed(self, combobox):
        """Event for selected language."""
        self.set_locale(combobox.get_active_id())

    def on_action_clicked(self, action, _=None):
        """Event for differents actions."""
        name = action.get_name()
        if name == "install":
            subprocess.Popen(["calamares_polkit"])
        elif name == "autostart":
            self.set_autostart(action.get_active())
        elif name == "about":
            dialog = self.builder.get_object("aboutdialog")
            dialog.run()
            dialog.hide()
        elif name == "appBrowser":
            # or use only "on_btn_clicked" ?
            self.builder.get_object("home").set_sensitive(not name == "home")
            self.builder.get_object("stack").set_visible_child_name(name + "page")

    def on_btn_clicked(self, btn):
        """Event for applications button."""
        name = btn.get_name()
        self.builder.get_object("home").set_sensitive(not name == "home")
        self.builder.get_object("stack").set_visible_child_name(name + "page")

    def on_link_clicked(self, link, _=None):
        """Event for clicked link."""
        webbrowser.open_new_tab(self.preferences["urls"][link.get_name()])

    def on_delete_window(self, *args):
        """Event to quit app."""
        write_json(self.preferences["save_path"], self.save)
        Gtk.main_quit(*args)


def fix_path(path):
    """Make good paths.
    :param path: path to fix
    :type path: str
    :return: fixed path
    :rtype: str
    """
    if "~" in path:
        path = path.replace("~", os.path.expanduser("~"))
    return path


def read_json(path):
    """Read content of a json file.
    :param path: path to read
    :type path: str
    :return: json content
    :rtype: str
    """
    path = fix_path(path)
    try:
        with open(path, "r") as fil:
            return json.load(fil)
    except OSError:
        return None


def write_json(path, content):
    """Write content in a json file.
    :param path: path to write
    :type path: str
    :param content: content to write
    :type path: str
    """
    path = fix_path(path)
    try:
        with open(path, "w") as fil:
            json.dump(content, fil)
    except OSError as error:
        print(error)

def get_os_infos():
    """Read informations from the os-release file.
    :return: args from os-release file
    :rtype: dict"""
    os = {}
    try:
        with open("/etc/os-release") as os_release:
            for line in os_release:
                if "=" in line:
                    var, arg = line.rstrip().split("=")
                    if not arg:
                        continue
                    var = var.replace("VERSION_","")
                    os[var] = arg.strip('"')
    except (OSError, KeyError) as error:
        print(error)
        return 'not Gentoo base', '0.0'
    return os["NAME"], os["ID"], os["PRETTY_NAME"]


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    hello = Hello()
    hello.connect("destroy", Gtk.main_quit)
    Gtk.main()
