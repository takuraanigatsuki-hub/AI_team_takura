using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Win32;

namespace AITeamRoom.Installer;

internal static class InstallEngine
{
    public const string AppName = "AI Team Room";
    public const string ExeName = "AI_Team_Room.exe";
    private const string UninstallRegKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\AITeamRoom";
    private static readonly byte[] Entropy = Encoding.UTF8.GetBytes("AITeamRoom.v1.takura");

    public static string DefaultInstallPath =>
        Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "Programs",
            AppName);

    public static void WriteProtected(string path, string plaintext)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir))
            Directory.CreateDirectory(dir);
        var data = ProtectedData.Protect(Encoding.UTF8.GetBytes(plaintext), Entropy, DataProtectionScope.CurrentUser);
        File.WriteAllBytes(path, data);
    }

    public static async Task InstallAsync(
        string targetDir,
        bool desktopShortcut,
        bool startMenuShortcut,
        IProgress<(int pct, string msg)> progress,
        CancellationToken ct)
    {
        targetDir = Path.GetFullPath(targetDir.Trim());
        progress.Report((5, "Подготовка папки…"));
        ct.ThrowIfCancellationRequested();
        Directory.CreateDirectory(targetDir);

        progress.Report((15, "Распаковка приложения…"));
        ct.ThrowIfCancellationRequested();
        var exePath = Path.Combine(targetDir, ExeName);
        await ExtractEmbeddedExeAsync(exePath, ct);

        progress.Report((45, "Шифрование конфигурации…"));
        ct.ThrowIfCancellationRequested();
        var configJson = JsonSerializer.Serialize(new
        {
            Server = "http://80.78.245.66",
            Version = "1.1.0",
        }, new JsonSerializerOptions { WriteIndented = true });
        WriteProtected(Path.Combine(targetDir, "config.secure"), configJson);

        var metaJson = JsonSerializer.Serialize(new
        {
            InstallPath = targetDir,
            InstalledAt = DateTime.UtcNow.ToString("O"),
            DesktopShortcut = desktopShortcut,
            StartMenuShortcut = startMenuShortcut,
        }, new JsonSerializerOptions { WriteIndented = true });
        WriteProtected(Path.Combine(targetDir, "install.meta.secure"), metaJson);

        progress.Report((60, "Создание ярлыков…"));
        ct.ThrowIfCancellationRequested();
        if (desktopShortcut)
        {
            var desktop = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                $"{AppName}.lnk");
            CreateShortcut(exePath, desktop);
        }
        if (startMenuShortcut)
        {
            var menu = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.StartMenu),
                "Programs",
                $"{AppName}.lnk");
            Directory.CreateDirectory(Path.GetDirectoryName(menu)!);
            CreateShortcut(exePath, menu);
        }

        progress.Report((80, "Регистрация в системе…"));
        ct.ThrowIfCancellationRequested();
        RegisterUninstall(targetDir, exePath);

        progress.Report((100, "Готово"));
    }

    static async Task ExtractEmbeddedExeAsync(string destPath, CancellationToken ct)
    {
        var asm = Assembly.GetExecutingAssembly();
        var names = asm.GetManifestResourceNames();
        var resourceName = names.FirstOrDefault(n => n.EndsWith("AI_Team_Room.exe", StringComparison.OrdinalIgnoreCase));
        if (resourceName == null)
            throw new FileNotFoundException("Встроенный AI_Team_Room.exe не найден. Пересоберите установщик.");

        await using var stream = asm.GetManifestResourceStream(resourceName)
            ?? throw new FileNotFoundException("Не удалось прочитать встроенный exe.");
        await using var fs = new FileStream(destPath, FileMode.Create, FileAccess.Write, FileShare.None);
        var buffer = new byte[81920];
        int read;
        while ((read = await stream.ReadAsync(buffer, ct)) > 0)
            await fs.WriteAsync(buffer.AsMemory(0, read), ct);
    }

    static void CreateShortcut(string target, string shortcutPath)
    {
        var ps = $"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcutPath.Replace("'", "''")}')
$Shortcut.TargetPath = '{target.Replace("'", "''")}'
$Shortcut.WorkingDirectory = '{Path.GetDirectoryName(target)!.Replace("'", "''")}'
$Shortcut.Description = '{AppName}'
$Shortcut.Save()
""";
        var tmp = Path.Combine(Path.GetTempPath(), "aitr-shortcut.ps1");
        File.WriteAllText(tmp, ps, Encoding.UTF8);
        try
        {
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = "powershell",
                Arguments = $"-NoProfile -ExecutionPolicy Bypass -File \"{tmp}\"",
                CreateNoWindow = true,
                UseShellExecute = false,
            })?.WaitForExit(15000);
        }
        finally
        {
            try { File.Delete(tmp); } catch { /* ignore */ }
        }
    }

    static void RegisterUninstall(string installDir, string exePath)
    {
        using var key = Registry.CurrentUser.CreateSubKey(UninstallRegKey);
        key.SetValue("DisplayName", AppName);
        key.SetValue("DisplayVersion", "1.1.0");
        key.SetValue("Publisher", "Takura");
        key.SetValue("InstallLocation", installDir);
        key.SetValue("DisplayIcon", exePath);
        key.SetValue("UninstallString", $"\"{exePath}\" --uninstall");
        key.SetValue("NoModify", 1, RegistryValueKind.DWord);
        key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
    }
}
