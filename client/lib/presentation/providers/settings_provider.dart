import 'dart:io';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class SettingsProvider extends ChangeNotifier {
  static const String _baseUrlKey = 'base_url';
  static const String _themeModeKey = 'theme_mode';
  static const String _useLocalLlmKey = 'use_local_llm';

  // Default values
  String _baseUrl = 'http://10.0.2.2:8000';
  ThemeMode _themeMode = ThemeMode.system;
  bool _useLocalLlm = false;

  String get baseUrl => _baseUrl;
  ThemeMode get themeMode => _themeMode;
  bool get useLocalLlm => _useLocalLlm;

  SettingsProvider() {
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    String defaultUrl = 'http://10.0.2.2:8000';
    try {
      if (Platform.isAndroid) {
        defaultUrl = 'http://10.0.2.2:8000';
      } else {
        defaultUrl = 'http://localhost:8000';
      }
    } catch (e) {
      // Platform check might fail on web, default to localhost
      defaultUrl = 'http://localhost:8000';
    }

    _baseUrl = prefs.getString(_baseUrlKey) ?? defaultUrl;

    final themeIndex = prefs.getInt(_themeModeKey);
    if (themeIndex != null) {
      _themeMode = ThemeMode.values[themeIndex];
    }

    _useLocalLlm = prefs.getBool(_useLocalLlmKey) ?? false;
    notifyListeners();
  }

  Future<void> setBaseUrl(String url) async {
    _baseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_baseUrlKey, url);
    notifyListeners();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_themeModeKey, mode.index);
    notifyListeners();
  }

  Future<void> setUseLocalLlm(bool useLocal) async {
    _useLocalLlm = useLocal;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_useLocalLlmKey, useLocal);
    notifyListeners();
  }
}
