namespace AITeamRoom.Installer;

internal sealed class InstallerForm : Form
{
    private int _step;
    private readonly StepRail _rail = new();
    private readonly Panel _body = new() { Dock = DockStyle.Fill, Padding = new Padding(28, 12, 28, 8) };
    private readonly Panel _scrollHost = new() { Dock = DockStyle.Fill, AutoScroll = true };
    private readonly Panel _content = new()
    {
        Dock = DockStyle.Top,
        AutoSize = true,
        AutoSizeMode = AutoSizeMode.GrowAndShrink,
        MinimumSize = new Size(540, 220),
    };
    private readonly Panel _footer = new() { Dock = DockStyle.Bottom, Height = 68, Padding = new Padding(24, 14, 24, 14) };
    private readonly Button _back = new() { Text = "Назад", Width = 100, Height = 38 };
    private readonly Button _next = new() { Text = "Далее", Width = 132, Height = 38 };
    private readonly GradientProgressBar _progress = new() { Visible = false, Margin = new Padding(28, 0, 28, 6) };
    private readonly Label _status = new()
    {
        AutoSize = false,
        Height = 22,
        Visible = false,
        ForeColor = InstallerTheme.Muted,
        TextAlign = ContentAlignment.MiddleLeft,
        Dock = DockStyle.Top,
        Padding = new Padding(28, 0, 28, 4),
    };

    private TextBox _pathBox = null!;
    private CheckBox _chkDesktop = null!;
    private CheckBox _chkMenu = null!;
    private CheckBox _chkLaunch = null!;
    private string _installPath = InstallEngine.DefaultInstallPath;
    private bool _installOk;
    private bool _transitioning;

    public InstallerForm()
    {
        Text = "AI Team Room — установка";
        ClientSize = new Size(620, 520);
        FormBorderStyle = FormBorderStyle.None;
        MaximizeBox = false;
        MinimizeBox = false;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = InstallerTheme.Bg;
        ForeColor = InstallerTheme.Text;
        Font = InstallerTheme.FontUi;
        InstallerTheme.EnableDoubleBuffer(this);

        var titleBar = new InstallerTitleBar(this);

        InstallerTheme.StyleGhostButton(_back);
        InstallerTheme.StylePrimaryButton(_next);
        _back.Anchor = AnchorStyles.Right | AnchorStyles.Bottom;
        _next.Anchor = AnchorStyles.Right | AnchorStyles.Bottom;
        _back.Location = new Point(360, 14);
        _next.Location = new Point(468, 14);
        _back.Click += (_, _) =>
        {
            if (_step <= 0 || _transitioning) return;
            var target = _step == 3 && !_installOk ? 1 : _step - 1;
            _ = GoToStepAsync(target);
        };
        _next.Click += (_, _) => OnNext();

        _footer.Controls.Add(_back);
        _footer.Controls.Add(_next);
        _footer.BackColor = InstallerTheme.Surface;
        _footer.Paint += (_, e) =>
        {
            using var pen = new Pen(InstallerTheme.Border, 1f);
            e.Graphics.DrawLine(pen, 0, 0, _footer.Width, 0);
        };

        _scrollHost.Controls.Add(_content);
        _body.Controls.Add(_scrollHost);

        Controls.Add(_body);
        Controls.Add(_status);
        Controls.Add(_progress);
        Controls.Add(_footer);
        Controls.Add(_rail);
        Controls.Add(titleBar);

        Load += (_, _) => InstallerTheme.ApplyFormShadow(this);
        Shown += async (_, _) => await GoToStepAsync(0, instant: true);
    }

    async Task GoToStepAsync(int step, bool instant = false)
    {
        if (_transitioning || step == _step && !instant) return;
        _transitioning = true;
        _next.Enabled = false;
        _back.Enabled = false;

        if (!instant)
        {
            for (var i = 0; i < 8; i++)
            {
                _body.Padding = new Padding(28, 12 + i * 2, 28, 8);
                await Task.Delay(18);
            }
        }

        _step = step;
        _rail.AnimateTo(step);
        RebuildStep();
        UpdateChrome();

        if (!instant)
        {
            for (var i = 8; i >= 0; i--)
            {
                _body.Padding = new Padding(28, 12 + i * 2, 28, 8);
                await Task.Delay(16);
            }
        }
        _body.Padding = new Padding(28, 12, 28, 8);

        _transitioning = false;
        UpdateChrome();
    }

    void UpdateChrome()
    {
        _progress.Visible = _step == 2;
        _status.Visible = _step == 2;
        _back.Enabled = (_step == 1 || (_step == 3 && !_installOk)) && !_transitioning;
        _next.Enabled = _step != 2 && !_transitioning;
        _next.Text = _step switch
        {
            0 => "Начать →",
            1 => "Установить",
            3 when !_installOk => "Закрыть",
            3 => "Готово",
            _ => "Далее",
        };
    }

    void RebuildStep()
    {
        _content.Controls.Clear();
        switch (_step)
        {
            case 0: BuildWelcome(); break;
            case 1: BuildPath(); break;
            case 2: BuildProgress(); break;
            case 3: BuildDone(); break;
        }
        _content.PerformLayout();
    }

    void BuildWelcome()
    {
        var hero = new HeroPanel { Emoji = "🤖", Title = "Добро пожаловать", Dock = DockStyle.Top };
        var intro = MakeMuted(
            "Установите нативный клиент AI Team Room — рабочая область с 3D-студией, Kanban и чатом с 13 агентами.");
        var features = new FeatureList();
        features.SetItems([
            "Подключение к серверу takura",
            "Splash, вход через браузер, handoff",
            "Конфигурация шифруется (Windows DPAPI)",
            "Ярлыки на рабочем столе и в меню Пуск",
        ]);
        _content.Controls.Add(features);
        _content.Controls.Add(intro);
        _content.Controls.Add(hero);
    }

    void BuildPath()
    {
        AddHead("Папка установки");
        AddMuted("Выберите каталог. Конфигурация будет сохранена в зашифрованных файлах рядом с приложением.");

        var pathPanel = new Panel { Height = 88, Dock = DockStyle.Top, Padding = new Padding(0, 8, 0, 0) };

        _pathBox = new TextBox
        {
            Text = _installPath,
            Location = new Point(0, 4),
            Width = 420,
            Anchor = AnchorStyles.Left | AnchorStyles.Top | AnchorStyles.Right,
        };
        InstallerTheme.StyleTextBox(_pathBox);

        var browse = new Button
        {
            Text = "Обзор…",
            Location = new Point(432, 2),
            Size = new Size(88, 30),
            Anchor = AnchorStyles.Top | AnchorStyles.Right,
        };
        InstallerTheme.StyleGhostButton(browse);
        browse.Click += (_, _) => BrowseFolder();

        _chkDesktop = new CheckBox
        {
            Text = "Ярлык на рабочем столе",
            Checked = true,
            Location = new Point(0, 44),
            AutoSize = true,
            ForeColor = InstallerTheme.Text,
        };
        _chkMenu = new CheckBox
        {
            Text = "Ярлык в меню Пуск",
            Checked = true,
            Location = new Point(0, 68),
            AutoSize = true,
            ForeColor = InstallerTheme.Text,
        };

        pathPanel.Controls.AddRange([_pathBox, browse, _chkDesktop, _chkMenu]);
        pathPanel.Resize += (_, _) =>
        {
            browse.Left = Math.Max(0, pathPanel.Width - browse.Width);
            _pathBox.Width = Math.Max(120, browse.Left - 8);
        };

        _content.Controls.Add(pathPanel);
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
        AddHead(_installOk ? "Готово!" : "Не удалось установить");

        var badgeRow = new Panel { Height = 76, Dock = DockStyle.Top };
        var badge = new SuccessBadge { Failed = !_installOk, Location = new Point(0, 4) };
        badge.Play();
        badgeRow.Controls.Add(badge);

        AddMuted(_installOk
            ? $"Приложение установлено:\n{_installPath}\n\nconfig.secure и install.meta.secure зашифрованы для вашей учётной записи Windows."
            : "Выберите другую папку или проверьте права на запись, затем нажмите «Назад» и попробуйте снова.");

        if (_installOk)
        {
            _chkLaunch = new CheckBox
            {
                Text = "Запустить AI Team Room после закрытия",
                Checked = true,
                AutoSize = true,
                ForeColor = InstallerTheme.Text,
                Dock = DockStyle.Top,
                Padding = new Padding(0, 4, 0, 0),
            };
            _content.Controls.Add(_chkLaunch);
        }

        _content.Controls.Add(badgeRow);
    }

    void BrowseFolder()
    {
        using var dlg = new FolderBrowserDialog
        {
            Description = "Папка для AI Team Room",
            UseDescriptionForTitle = true,
            SelectedPath = Directory.Exists(_pathBox.Text)
                ? _pathBox.Text
                : InstallEngine.DefaultInstallPath,
        };
        if (dlg.ShowDialog(this) == DialogResult.OK)
            _pathBox.Text = Path.Combine(dlg.SelectedPath, InstallEngine.AppName);
    }

    async void OnNext()
    {
        if (_transitioning) return;

        if (_step == 0)
        {
            await GoToStepAsync(1);
            return;
        }

        if (_step == 1)
        {
            _installPath = _pathBox.Text.Trim();
            if (string.IsNullOrWhiteSpace(_installPath))
            {
                ShowToast("Укажите папку установки.");
                return;
            }

            try
            {
                _installPath = Path.GetFullPath(_installPath);
                Directory.CreateDirectory(_installPath);
            }
            catch (Exception ex)
            {
                ShowToast($"Недоступная папка: {ex.Message}");
                return;
            }

            await GoToStepAsync(2);
            await RunInstallAsync();
            return;
        }

        if (_step == 3)
        {
            if (_installOk && _chkLaunch?.Checked == true)
                LaunchApp();
            Close();
        }
    }

    async Task RunInstallAsync()
    {
        _next.Enabled = false;
        _back.Enabled = false;
        var progress = new Progress<(int pct, string msg)>(p =>
        {
            if (IsDisposed) return;
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
            _status.Text = ex.Message;
            ShowToast(ex.Message);
        }

        await GoToStepAsync(3);
    }

    void LaunchApp()
    {
        var exe = Path.Combine(_installPath, InstallEngine.ExeName);
        if (!File.Exists(exe)) return;
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

    void ShowToast(string message)
    {
        MessageBox.Show(this, message, Text, MessageBoxButtons.OK,
            MessageBoxIcon.Information);
    }

    CheckBox MakeCheck(string text, bool check, int top) => new()
    {
        Text = text,
        Checked = check,
        Location = new Point(0, top),
        AutoSize = true,
        ForeColor = InstallerTheme.Text,
    };

    void AddHead(string text)
    {
        _content.Controls.Add(new Label
        {
            Text = text,
            Font = InstallerTheme.FontHead,
            ForeColor = InstallerTheme.Text,
            AutoSize = true,
            Dock = DockStyle.Top,
            Margin = new Padding(0, 0, 0, 4),
        });
    }

    Label MakeMuted(string text) => new()
    {
        Text = text,
        ForeColor = InstallerTheme.Muted,
        Font = InstallerTheme.FontUi,
        MaximumSize = new Size(540, 0),
        AutoSize = true,
        Dock = DockStyle.Top,
        Margin = new Padding(0, 0, 0, 8),
    };

    void AddMuted(string text) => _content.Controls.Add(MakeMuted(text));
}
