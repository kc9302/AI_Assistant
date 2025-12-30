import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:client/presentation/providers/settings_provider.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final TextEditingController _urlController = TextEditingController();

  @override
  void initState() {
    super.initState();
    final settings = context.read<SettingsProvider>();
    _urlController.text = settings.baseUrl;
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: Consumer<SettingsProvider>(
        builder: (context, settings, child) {
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Theme Settings
              ListTile(
                title: const Text('Theme'),
                leading: const Icon(Icons.brightness_6),
                trailing: DropdownButton<ThemeMode>(
                  value: settings.themeMode,
                  onChanged: (ThemeMode? newValue) {
                    if (newValue != null) {
                      settings.setThemeMode(newValue);
                    }
                  },
                  items: const [
                    DropdownMenuItem(
                      value: ThemeMode.system,
                      child: Text('System'),
                    ),
                    DropdownMenuItem(
                      value: ThemeMode.light,
                      child: Text('Light'),
                    ),
                    DropdownMenuItem(
                      value: ThemeMode.dark,
                      child: Text('Dark'),
                    ),
                  ],
                ),
              ),
              const Divider(),

              // Backend URL Settings
              ListTile(
                title: const Text('Backend URL'),
                leading: const Icon(Icons.link),
                subtitle: Text(settings.baseUrl),
                onTap: () {
                  showDialog(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: const Text('Set Backend URL'),
                      content: TextField(
                        controller: _urlController,
                        decoration: const InputDecoration(
                          hintText: 'http://10.0.2.2:8000',
                          labelText: 'URL',
                        ),
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('Cancel'),
                        ),
                        TextButton(
                          onPressed: () {
                            settings.setBaseUrl(_urlController.text);
                            Navigator.pop(context);
                          },
                          child: const Text('Save'),
                        ),
                      ],
                    ),
                  );
                },
              ),
              const Divider(),

              // Model Selection
              SwitchListTile(
                title: const Text('Use Local LLM (FunctionGemma)'),
                subtitle: const Text('Run model on-device (Offline)'),
                value: settings.useLocalLlm,
                onChanged: (bool value) {
                  settings.setUseLocalLlm(value);
                },
                secondary: const Icon(Icons.memory),
              ),
            ],
          );
        },
      ),
    );
  }
}
