namespace AITeamRoom.Installer;

internal static class Program
{
    [STAThread]
    static void Main()
    {
        try
        {
            ApplicationConfiguration.Initialize();
            Application.SetHighDpiMode(HighDpiMode.PerMonitorV2);
            Application.Run(new InstallerForm());
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Не удалось запустить установщик:\n{ex.Message}\n\nПопробуйте «Запуск от имени администратора» или скачайте portable AI_Team_Room.exe.",
                "AI Team Room Setup",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }
}
