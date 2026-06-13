namespace AITeamRoom;

internal sealed class SettingsForm : Form
{
    private readonly TextBox _serverBox;
    private readonly string _installDir;

    public SettingsForm(string installDir, string currentServer)
    {
        _installDir = installDir;
        Text = "Настройки — AI Team Room";
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        MinimizeBox = false;
        StartPosition = FormStartPosition.CenterParent;
        ClientSize = new Size(440, 200);
        BackColor = AppTheme.Bg;
        ForeColor = AppTheme.Text;
        Font = AppTheme.FontUi;

        var title = new Label
        {
            Text = "Сервер подключения",
            Font = AppTheme.FontTitle,
            AutoSize = true,
            Location = new Point(20, 16),
            ForeColor = AppTheme.Text,
        };
        var hint = new Label
        {
            Text = "URL сохраняется в зашифрованном config.secure",
            AutoSize = true,
            Location = new Point(20, 42),
            ForeColor = AppTheme.Muted,
            Font = new Font("Segoe UI", 8.5F),
        };
        _serverBox = new TextBox
        {
            Location = new Point(20, 72),
            Width = 400,
            Text = currentServer,
        };
        AppTheme.StyleTextBox(_serverBox);

        var save = new Button
        {
            Text = "Сохранить",
            Location = new Point(228, 128),
            Size = new Size(92, 34),
            DialogResult = DialogResult.OK,
        };
        AppTheme.StylePrimaryButton(save);

        var cancel = new Button
        {
            Text = "Отмена",
            Location = new Point(328, 128),
            Size = new Size(92, 34),
            DialogResult = DialogResult.Cancel,
        };
        AppTheme.StyleGhostButton(cancel);

        Controls.AddRange([title, hint, _serverBox, save, cancel]);
        AcceptButton = save;
        CancelButton = cancel;
    }

    public string ServerUrl => _serverBox.Text.Trim().TrimEnd('/');

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (DialogResult == DialogResult.OK)
        {
            if (string.IsNullOrWhiteSpace(ServerUrl) ||
                (!ServerUrl.StartsWith("http://", StringComparison.OrdinalIgnoreCase) &&
                 !ServerUrl.StartsWith("https://", StringComparison.OrdinalIgnoreCase)))
            {
                MessageBox.Show(this, "Укажите корректный URL (http:// или https://)", "AI Team Room",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                e.Cancel = true;
                return;
            }
            var cfg = SecureStorage.LoadConfig(_installDir) ?? new AppConfig();
            cfg.Server = ServerUrl;
            SecureStorage.SaveConfig(_installDir, cfg);
        }
        base.OnFormClosing(e);
    }
}
