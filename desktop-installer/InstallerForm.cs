using System.Drawing.Drawing2D;

namespace AITeamRoom.Installer;

internal sealed class InstallerForm : Form
{
    private int _step;
    private readonly Panel _content = new() { Dock = DockStyle.Fill, Padding = new Padding(28, 20, 28, 16) };
    private readonly Panel _footer = new() { Dock = DockStyle.Bottom, Height = 64, Padding = new Padding(20, 12, 20, 12) };
    private readonly Label _stepLabel = new();
    private readonly Button _back = new() { Text = "Назад", Width = 96, Height = 36 };
    private readonly Button _next = new() { Text = "Далее", Width = 120, Height = 36 };
    private readonly ProgressBar _progress = new() { Style = ProgressBarStyle.Continuous, Height = 8, Visible = false };
    private readonly Label _status = new() { AutoSize = true, Visible = false, ForeColor = AppTheme.Muted };

    private TextBox _pathBox = null!;
    private CheckBox _chkDesktop = null!;
    private CheckBox _chkMenu = null!;
    private CheckBox _chkLaunch = null!;
    private string _installPath = InstallEngine.DefaultInstallPath;
    private bool _installOk;

    public InstallerForm()
    {
        Text = "AI Team Room — установка";
        ClientSize = new Size(560, 420);
        FormBorderStyle = FormBorderStyle.FixedSingle;
        MaximizeBox = false;
        MinimizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = AppTheme.Bg;
        ForeColor = AppTheme.Text;
        Font = AppTheme.FontUi;

        var header = new Panel { Dock = DockStyle.Top, Height = 56, BackColor = AppTheme.Surface };
        header.Paint += (_, e) =>
        {
            var r = new Rectangle(0, header.Height - 2, header.Width, 2);
            AppTheme.PaintGradientAccent(e.Graphics, r);
        };
        var logo = new Label
        {
            Text = "🤖  AI Team Room",
            Font = AppTheme.FontTitle,
            ForeColor = AppTheme.Text,
            AutoSize = true,
            Location = new Point(20, 16),
        };
        _stepLabel.ForeColor = AppTheme.Muted;
        _stepLabel.Font = new Font("Segoe UI", 8.5F);
        _stepLabel.AutoSize = true;
        _stepLabel.Location = new Point(380, 20);
        header.Controls.Add(logo);
        header.Controls.Add(_stepLabel);

        AppTheme.StyleGhostButton(_back);
        AppTheme.StylePrimaryButton(_next);
        _back.Anchor = AnchorStyles.Right | AnchorStyles.Bottom;
        _next.Anchor = AnchorStyles.Right | AnchorStyles.Bottom;
        _back.Location = new Point(320, 12);
        _next.Location = new Point(424, 12);
        _back.Click += (_, _) => { if (_step > 0) ShowStep(_step - 1); };
        _next.Click += (_, _) => OnNext();

        _footer.Controls.Add(_back);
        _footer.Controls.Add(_next);
        _footer.BackColor = AppTheme.Surface;

        _progress.Dock = DockStyle.Bottom;
        _progress.ForeColor = AppTheme.Accent;
        _status.Dock = DockStyle.Bottom;
        _status.Padding = new Padding(28, 0, 28, 8);

        Controls.Add(_content);
        Controls.Add(_status);
        Controls.Add(_progress);
        Controls.Add(_footer);
        Controls.Add(header);

        ShowStep(0);
    }

    void ShowStep(int step)
    {
        _step = step;
        _content.Controls.Clear();
        _progress.Visible = step == 2;
        _status.Visible = step == 2;
        _back.Enabled = step is 1 or 3;
        _next.Text = step switch
        {
            0 => "Далее",
            1 => "Установить",
            2 => "…",
            3 => "Готово",
            _ => "Далее",
        };
        _next.Enabled = step != 2;
        _stepLabel.Text = $"Шаг {step + 1} / 4";

        switch (step)
        {
            case 0: BuildWelcome(); break;
            case 1: BuildPath(); break;
            case 2: BuildProgress(); break;
            case 3: BuildDone(); break;
        }
    }

    void BuildWelcome()
    {
        AddHead("Добро пожаловать");
        AddMuted("Установите нативный клиент AI Team Room — рабочая область, 3D-студия, Kanban и чат с 13 агентами.");
        AddBullets([
            "Подключение к серверу takura",
            "Splash, вход через браузер, handoff",
            "Конфигурация шифруется (Windows DPAPI)",
            "Ярлыки на рабочем столе и в меню Пуск",
        ]);
    }

    void BuildPath()
    {
        AddHead("Папка установки");
        AddMuted("Выберите, куда сохранить приложение и зашифрованные файлы конфигурации.");

        _pathBox = new TextBox
        {
            Text = _installPath,
            Width = 380,
            Location = new Point(0, 108),
        };
        AppTheme.StyleTextBox(_pathBox);

        var browse = new Button
        {
            Text = "Обзор…",
            Location = new Point(392, 106),
            Size = new Size(88, 28),
        };
        AppTheme.StyleGhostButton(browse);
        browse.Click += (_, _) =>
        {
            using var dlg = new FolderBrowserDialog
            {
                Description = "Папка для AI Team Room",
                SelectedPath = Directory.Exists(_pathBox.Text) ? _pathBox.Text : InstallEngine.DefaultInstallPath,
            };
            if (dlg.ShowDialog(this) == DialogResult.OK)
                _pathBox.Text = Path.Combine(dlg.SelectedPath, "AI Team Room");
        };

        _chkDesktop = new CheckBox
        {
            Text = "Ярлык на рабочем столе",
            Checked = true,
            Location = new Point(0, 148),
            AutoSize = true,
            ForeColor = AppTheme.Text,
        };
        _chkMenu = new CheckBox
        {
            Text = "Ярлык в меню Пуск",
            Checked = true,
            Location = new Point(0, 174),
            AutoSize = true,
            ForeColor = AppTheme.Text,
        };

        _content.Controls.AddRange([_pathBox, browse, _chkDesktop, _chkMenu]);
    }

    void BuildProgress()
    {
        AddHead("Установка…");
        AddMuted("Копирование файлов и шифрование конфигурации. Не закрывайте окно.");
        _progress.Value = 0;
        _status.Text = "Старт…";
    }

    void BuildDone()
    {
        AddHead(_installOk ? "Установка завершена ✓" : "Ошибка установки");
        AddMuted(_installOk
            ? $"Приложение установлено в:\n{_installPath}\n\nconfig.secure и install.meta.secure зашифрованы для вашей учётной записи Windows."
            : "Попробуйте другую папку или запустите установщик от имени пользователя с правами на запись.");

        if (_installOk)
        {
            _chkLaunch = new CheckBox
            {
                Text = "Запустить AI Team Room",
                Checked = true,
                Location = new Point(0, 160),
                AutoSize = true,
                ForeColor = AppTheme.Text,
            };
            _content.Controls.Add(_chkLaunch);
        }
    }

    async void OnNext()
    {
        if (_step == 0)
        {
            ShowStep(1);
            return;
        }
        if (_step == 1)
        {
            _installPath = _pathBox.Text.Trim();
            if (string.IsNullOrWhiteSpace(_installPath))
            {
                MessageBox.Show(this, "Укажите папку установки.", Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            try
            {
                _installPath = Path.GetFullPath(_installPath);
                Directory.CreateDirectory(_installPath);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, $"Недоступная папка:\n{ex.Message}", Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            ShowStep(2);
            await RunInstallAsync();
            return;
        }
        if (_step == 3)
        {
            if (_installOk && _chkLaunch?.Checked == true)
            {
                var exe = Path.Combine(_installPath, InstallEngine.ExeName);
                if (File.Exists(exe))
                {
                    try
                    {
                        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(exe)
                        {
                            UseShellExecute = true,
                            WorkingDirectory = _installPath,
                        });
                    }
                    catch { /* ignore */ }
                }
            }
            Close();
        }
    }

    async Task RunInstallAsync()
    {
        _next.Enabled = false;
        _back.Enabled = false;
        var progress = new Progress<(int pct, string msg)>(p =>
        {
            _progress.Value = Math.Clamp(p.pct, 0, 100);
            _status.Text = p.msg;
        });
        try
        {
            await InstallEngine.InstallAsync(
                _installPath,
                _chkDesktop.Checked,
                _chkMenu.Checked,
                progress,
                CancellationToken.None);
            _installOk = true;
        }
        catch (Exception ex)
        {
            _installOk = false;
            MessageBox.Show(this, ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        ShowStep(3);
    }

    void AddHead(string text)
    {
        _content.Controls.Add(new Label
        {
            Text = text,
            Font = AppTheme.FontHead,
            ForeColor = AppTheme.Text,
            AutoSize = true,
            Location = new Point(0, 0),
        });
    }

    void AddMuted(string text)
    {
        _content.Controls.Add(new Label
        {
            Text = text,
            ForeColor = AppTheme.Muted,
            Font = AppTheme.FontUi,
            Location = new Point(0, 44),
            MaximumSize = new Size(480, 0),
            AutoSize = true,
        });
    }

    void AddBullets(string[] items)
    {
        var y = 120;
        foreach (var item in items)
        {
            _content.Controls.Add(new Label
            {
                Text = "▸  " + item,
                ForeColor = AppTheme.Text,
                Location = new Point(0, y),
                AutoSize = true,
            });
            y += 26;
        }
    }
}

internal static class AppTheme
{
    public static readonly Color Bg = Color.FromArgb(10, 11, 16);
    public static readonly Color Surface = Color.FromArgb(18, 20, 28);
    public static readonly Color Surface2 = Color.FromArgb(24, 27, 38);
    public static readonly Color Text = Color.FromArgb(242, 243, 247);
    public static readonly Color Muted = Color.FromArgb(148, 150, 168);
    public static readonly Color Accent = Color.FromArgb(139, 92, 246);
    public static readonly Color Accent2 = Color.FromArgb(122, 162, 255);

    public static readonly Font FontUi = new("Segoe UI", 9F);
    public static readonly Font FontTitle = new("Segoe UI Semibold", 11F, FontStyle.Bold);
    public static readonly Font FontHead = new("Segoe UI", 18F, FontStyle.Bold);

    public static void StylePrimaryButton(Button btn)
    {
        btn.FlatStyle = FlatStyle.Flat;
        btn.FlatAppearance.BorderSize = 0;
        btn.BackColor = Accent;
        btn.ForeColor = Color.White;
        btn.Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold);
        btn.Cursor = Cursors.Hand;
    }

    public static void StyleGhostButton(Button btn)
    {
        btn.FlatStyle = FlatStyle.Flat;
        btn.FlatAppearance.BorderColor = Color.FromArgb(40, 255, 255, 255);
        btn.FlatAppearance.BorderSize = 1;
        btn.BackColor = Surface2;
        btn.ForeColor = Text;
        btn.Cursor = Cursors.Hand;
    }

    public static void StyleTextBox(TextBox tb)
    {
        tb.BackColor = Surface2;
        tb.ForeColor = Text;
        tb.BorderStyle = BorderStyle.FixedSingle;
    }

    public static void PaintGradientAccent(Graphics g, Rectangle bounds)
    {
        using var brush = new LinearGradientBrush(bounds, Accent, Accent2, LinearGradientMode.Horizontal);
        g.FillRectangle(brush, bounds);
    }
}
