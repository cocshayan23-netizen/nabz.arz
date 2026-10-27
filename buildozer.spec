[app]
title = NABZ
package.name = nabz
package.domain = ir.nabz
source.dir = .
source.include_exts = py,png,jpg,kv,ttf,json
version = 1.0
requirements = python3,kivy==2.3.0,arabic-reshaper==3.0.0,python-bidi==0.4.2,six,plyer,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,POST_NOTIFICATIONS
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
