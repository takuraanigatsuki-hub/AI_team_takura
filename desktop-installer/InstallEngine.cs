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
    public const string UpdaterExeName = "AI_Team_Room_Updater.exe";
    public const string UninstallExeName = "AI_Team_Room_Uninstall.exe";
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

        progress.Report((10, "Распаковка приложения…"));
        ct.ThrowIfCancellationRequested();
        var exePath = Path.Combine(targetDir, ExeName);
        await ExtractEmbeddedExeAsync("AI_Team_Room.exe", exePath, progress, 12, 35, ct);

        progress.Report((38, "Установка updater…"));
        ct.ThrowIfCancellationRequested();
        var updaterPath = Path.Combine(targetDir, UpdaterExeName);
        await ExtractEmbeddedExeAsync("AI_Team_Room_Updater.exe", updaterPath, progress, 38, 44, ct);

        progress.Report((46, "Установка удаления…"));
        ct.ThrowIfCancellationRequested();
        var uninstallPath = Path.Combine(targetDir, UninstallExeName);
        await ExtractEmbeddedExeAsync("AI_Team_Room_Uninstall.exe", uninstallPath, progress, 46, 52, ct);

        progress.Report((54, "Шифрование конфигурации…"));
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

        progress.Report((66, "Создание ярлыков…"));
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

        progress.Report((84, "Регистрация в системе…"));
        ct.ThrowIfCancellationRequested();
        RegisterUninstall(targetDir, exePath, uninstallPath, updaterPath);

        progress.Report((100, "Готово"));
    }

    static async Task ExtractEmbeddedExeAsync(string destPath, IProgress<(int pct, string msg)>? progress, CancellationToken ct)
    {
        var asm = Assembly.GetExecutingAssembly();
        var names = asm.GetManifestResourceNames();
        var resourceName = names.FirstOrDefault(n =>
            n.EndsWith("AI_Team_Room.exe", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(n, "AI_Team_Room.exe", StringComparison.OrdinalIgnoreCase));
        if (resourceName == null)
            throw new FileNotFoundException(
                "Встроенный AI_Team_Room.exe не найден. Сначала выполните scripts\\build-desktop.ps1");

        await using var stream = asm.GetManifestResourceStream(resourceName)
            ?? throw new FileNotFoundException("Не удалось прочитать встроенный exe.");

        var total = stream.Length;
        if (total <= 0)
            throw new InvalidOperationException("Встроенный exe пустой — пересоберите установщик.");

        await using var fs = new FileStream(destPath, FileMode.Create, FileAccess.Write, FileShare.None);
        var buffer = new byte[81920];
        long copied;
        int read;
        for (copied = 0; (read = await stream.ReadAsync(buffer, ct)) > 0; copied += read)
        {
            await fs.WriteAsync(buffer.AsMemory(0, read), ct);
            var pct = 15 + (int)(copied * 28 / total);
            progress?.Report((pct, "Копирование приложения…"));
        }
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
