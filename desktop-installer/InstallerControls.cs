using System.Drawing.Drawing2D;

namespace AITeamRoom.Installer;

internal sealed class InstallerTitleBar : Panel
{
    private const int WmNcLButtonDown = 0xA1;
    private const int HtCaption = 0x2;

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern bool ReleaseCapture();

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern int SendMessage(IntPtr hWnd, int msg, int wParam, int lParam);

    private readonly Form _host;
    private float _accentPhase;

    public InstallerTitleBar(Form host)
    {
        _host = host;
        Height = 52;
        Dock = DockStyle.Top;
        BackColor = InstallerTheme.Surface;
        InstallerTheme.EnableDoubleBuffer(this);

        var logo = new Label
        {
            Text = "🤖  AI Team Room",
            Font = InstallerTheme.FontTitle,
            ForeColor = InstallerTheme.Text,
            AutoSize = true,
            Location = new Point(16, 14),
            BackColor = Color.Transparent,
        };

        var close = new Button
        {
            Text = "✕",
            Size = new Size(40, 32),
            Location = new Point(host.ClientSize.Width - 48, 10),
            Anchor = AnchorStyles.Top | AnchorStyles.Right,
            FlatStyle = FlatStyle.Flat,
            ForeColor = InstallerTheme.Muted,
            BackColor = Color.Transparent,
            Cursor = Cursors.Hand,
            TabStop = false,
        };
        close.FlatAppearance.BorderSize = 0;
        close.FlatAppearance.MouseOverBackColor = Color.FromArgb(48, InstallerTheme.Danger);
        close.FlatAppearance.MouseDownBackColor = InstallerTheme.Danger;
        close.Click += (_, _) => _host.Close();
        close.MouseEnter += (_, _) => close.ForeColor = Color.White;
        close.MouseLeave += (_, _) => close.ForeColor = InstallerTheme.Muted;

        Controls.Add(logo);
        Controls.Add(close);

        MouseDown += BeginDrag;
        logo.MouseDown += BeginDrag;

        var timer = new System.Windows.Forms.Timer { Interval = 40 };
        timer.Tick += (_, _) =>
        {
            _accentPhase = (_accentPhase + 0.04f) % 1f;
            Invalidate(new Rectangle(0, Height - 2, Width, 2));
        };
        timer.Start();
    }

    void BeginDrag(object? sender, MouseEventArgs e)
    {
        if (e.Button != MouseButtons.Left) return;
        ReleaseCapture();
        SendMessage(_host.Handle, WmNcLButtonDown, HtCaption, 0);
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        var w = Width;
        var shift = (int)(_accentPhase * w * 0.35f);
        var rect = new Rectangle(-shift, Height - 2, w + w / 2, 2);
        using var brush = new LinearGradientBrush(rect, InstallerTheme.Accent, InstallerTheme.Accent2, 0f);
        g.FillRectangle(brush, 0, Height - 2, w, 2);
    }
}

internal sealed class StepRail : Control
{
    private static readonly string[] Labels = ["Приветствие", "Папка", "Установка", "Готово"];
    private int _step;
    private float _anim;

    public StepRail()
    {
        Height = 56;
        Dock = DockStyle.Top;
        BackColor = Color.Transparent;
        InstallerTheme.EnableDoubleBuffer(this);
    }

    public int Step
    {
        get => _step;
        set
        {
            _step = Math.Clamp(value, 0, Labels.Length - 1);
            Invalidate();
        }
    }

    public void AnimateTo(int step)
    {
        _step = Math.Clamp(step, 0, Labels.Length - 1);
        _anim = 0f;
        var timer = new System.Windows.Forms.Timer { Interval = 16 };
        timer.Tick += (_, _) =>
        {
            _anim = Math.Min(1f, _anim + 0.12f);
            Invalidate();
            if (_anim >= 1f) timer.Stop();
        };
        timer.Start();
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;

        var count = Labels.Length;
        var pad = 36;
        var usable = Width - pad * 2;
        var stepW = usable / (count - 1);
        var y = 14;

        using var linePen = new Pen(Color.FromArgb(40, 255, 255, 255), 2f);
        g.DrawLine(linePen, pad, y, pad + usable, y);

        var progressX = pad + stepW * _step;
        using var progBrush = new LinearGradientBrush(
            new Rectangle(pad, y - 1, (int)(progressX - pad + 1), 4),
            InstallerTheme.Accent,
            InstallerTheme.Accent2,
            0f);
        if (progressX > pad)
            g.FillRectangle(progBrush, pad, y - 1, progressX - pad, 3);

        for (var i = 0; i < count; i++)
        {
            var cx = pad + stepW * i;
            var active = i <= _step;
            var current = i == _step;
            var r = current ? 9 : 7;
            var pulse = current ? 1f + _anim * 0.25f : 1f;
            r = (int)(r * pulse);

            using var glow = new SolidBrush(Color.FromArgb(current ? 40 : 0, InstallerTheme.Accent));
            if (current)
                g.FillEllipse(glow, cx - r - 4, y - r - 4, (r + 4) * 2, (r + 4) * 2);

            using var fill = new SolidBrush(active ? InstallerTheme.Accent : InstallerTheme.Surface2);
            g.FillEllipse(fill, cx - r, y - r, r * 2, r * 2);

            if (i < _step)
            {
                using var checkPen = new Pen(Color.White, 2f);
                g.DrawLine(checkPen, cx - 4, y, cx - 1, y + 3);
                g.DrawLine(checkPen, cx - 1, y + 3, cx + 5, y - 4);
            }
            else if (current)
            {
                using var inner = new SolidBrush(Color.White);
                g.FillEllipse(inner, cx - 3, y - 3, 6, 6);
            }

            using var textBrush = new SolidBrush(i == _step ? InstallerTheme.Text : InstallerTheme.Muted);
            var label = Labels[i];
            var size = g.MeasureString(label, InstallerTheme.FontUi);
            g.DrawString(label, InstallerTheme.FontUi, textBrush, cx - size.Width / 2, y + 14);
        }
    }
}

internal sealed class GradientProgressBar : Control
{
    private int _value;
    private float _display;
    private float _shimmer;
    private readonly System.Windows.Forms.Timer _timer;

    public GradientProgressBar()
    {
        Height = 10;
        Dock = DockStyle.Top;
        BackColor = Color.Transparent;
        InstallerTheme.EnableDoubleBuffer(this);
        _timer = new System.Windows.Forms.Timer { Interval = 16 };
        _timer.Tick += (_, _) =>
        {
            var target = _value;
            _display += (target - _display) * 0.18f;
            if (Math.Abs(_display - target) < 0.5f) _display = target;
            _shimmer = (_shimmer + 0.025f) % 1.5f;
            Invalidate();
        };
        _timer.Start();
    }

    public int Value
    {
        get => _value;
        set
        {
            _value = Math.Clamp(value, 0, 100);
            Invalidate();
        }
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        var bounds = new Rectangle(0, 0, Width - 1, Height - 1);

        using (var bgPath = InstallerTheme.RoundedRect(bounds, 5))
        using (var bg = new SolidBrush(Color.FromArgb(80, 255, 255, 255)))
            g.FillPath(bg, bgPath);

        var fillW = Math.Max(8, (int)(bounds.Width * (_display / 100f)));
        if (fillW <= 0) return;

        var fillRect = new Rectangle(0, 0, fillW, bounds.Height);
        using var fillPath = InstallerTheme.RoundedRect(fillRect, 5);
        using var grad = new LinearGradientBrush(fillRect, InstallerTheme.Accent, InstallerTheme.Accent2, 0f);
        g.SetClip(fillPath);
        g.FillPath(grad, fillPath);

        var shimmerX = (int)(fillW * _shimmer) - 40;
        using var shimmer = new LinearGradientBrush(
            new Rectangle(shimmerX, 0, 80, Height),
            Color.FromArgb(0, 255, 255, 255),
            Color.FromArgb(90, 255, 255, 255),
            0f);
        g.FillRectangle(shimmer, shimmerX, 0, 80, Height);
        g.ResetClip();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) _timer.Dispose();
        base.Dispose(disposing);
    }
}

internal sealed class HeroPanel : Panel
{
    private float _pulse;

    public HeroPanel()
    {
        Height = 88;
        Dock = DockStyle.Top;
        BackColor = Color.Transparent;
        InstallerTheme.EnableDoubleBuffer(this);
        var timer = new System.Windows.Forms.Timer { Interval = 40 };
        timer.Tick += (_, _) =>
        {
            _pulse = (_pulse + 0.03f) % 1f;
            Invalidate();
        };
        timer.Start();
    }

    public string Emoji { get; set; } = "🤖";
    public string Title { get; set; } = "";

    protected override void OnPaint(PaintEventArgs e)
    {
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;

        var card = new Rectangle(0, 4, Width, Height - 8);
        using var path = InstallerTheme.RoundedRect(card, 12);
        using var bg = new SolidBrush(InstallerTheme.Surface2);
        g.FillPath(bg, path);

        var glowSize = 52 + (int)(Math.Sin(_pulse * Math.PI * 2) * 4);
        var glowRect = new Rectangle(16, 16 + (88 - glowSize) / 2 - 8, glowSize, glowSize);
        using var glowBrush = new PathGradientBrush(new Point[] {
            new(glowRect.X + glowRect.Width / 2, glowRect.Y + glowRect.Height / 2),
            new(glowRect.Right, glowRect.Y),
            new(glowRect.Right, glowRect.Bottom),
            new(glowRect.X, glowRect.Bottom),
            new(glowRect.X, glowRect.Y),
        })
        {
            CenterColor = Color.FromArgb(55, InstallerTheme.Accent),
            SurroundColors = [Color.FromArgb(0, InstallerTheme.Accent)]
        };
        g.FillEllipse(glowBrush, glowRect);

        using var emojiFont = new Font("Segoe UI Emoji", 22F);
        g.DrawString(Emoji, emojiFont, Brushes.White, 24, 22);

        using var titleFont = InstallerTheme.FontHead;
        using var titleBrush = new SolidBrush(InstallerTheme.Text);
        g.DrawString(Title, titleFont, titleBrush, 88, 22);

        using var subBrush = new SolidBrush(InstallerTheme.Muted);
        g.DrawString("Установщик v1.1", InstallerTheme.FontSub, subBrush, 88, 54);
    }
}

internal sealed class FeatureList : Control
{
    private readonly List<(string text, float reveal)> _items = [];
    private readonly System.Windows.Forms.Timer _timer;

    public FeatureList()
    {
        Height = 140;
        Dock = DockStyle.Top;
        BackColor = Color.Transparent;
        InstallerTheme.EnableDoubleBuffer(this);
        _timer = new System.Windows.Forms.Timer { Interval = 20 };
        _timer.Tick += (_, _) =>
        {
            var done = true;
            for (var i = 0; i < _items.Count; i++)
            {
                if (_items[i].reveal < 1f)
                {
                    _items[i] = (_items[i].text, Math.Min(1f, _items[i].reveal + 0.08f));
                    done = false;
                }
            }
            Invalidate();
            if (done) _timer.Stop();
        };
    }

    public void SetItems(IEnumerable<string> items)
    {
        _items.Clear();
        foreach (var item in items)
            _items.Add((item, 0f));
        _timer.Start();
        Invalidate();
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        var g = e.Graphics;
        g.TextRenderingHint = System.Drawing.Text.TextRenderingHint.ClearTypeGridFit;
        var y = 8;
        foreach (var (text, reveal) in _items)
        {
            var slide = (int)((1f - reveal) * 24);
            var alpha = (int)(255 * reveal);
            using var dot = new SolidBrush(Color.FromArgb(alpha, InstallerTheme.Accent));
            g.FillEllipse(dot, 4, y + 4, 8, 8);
            using var brush = new SolidBrush(Color.FromArgb(alpha, InstallerTheme.Text));
            g.DrawString(text, InstallerTheme.FontUi, brush, 20 + slide, y);
            y += 28;
        }
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing) _timer.Dispose();
        base.Dispose(disposing);
    }
}

internal sealed class SuccessBadge : Control
{
    private float _progress;

    public SuccessBadge()
    {
        Size = new Size(72, 72);
        BackColor = Color.Transparent;
        InstallerTheme.EnableDoubleBuffer(this);
    }

    public bool Failed { get; set; }

    public void Play()
    {
        _progress = 0f;
        var timer = new System.Windows.Forms.Timer { Interval = 16 };
        timer.Tick += (_, _) =>
        {
            _progress = Math.Min(1f, _progress + 0.06f);
            Invalidate();
            if (_progress >= 1f) timer.Stop();
        };
        timer.Start();
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        var color = Failed ? InstallerTheme.Danger : InstallerTheme.Success;
        var r = 32;
        var cx = Width / 2;
        var cy = Height / 2;

        using var glow = new SolidBrush(Color.FromArgb((int)(40 * _progress), color));
        g.FillEllipse(glow, cx - r - 6, cy - r - 6, (r + 6) * 2, (r + 6) * 2);

        using var ringPen = new Pen(Color.FromArgb((int)(255 * _progress), color), 3f);
        g.DrawEllipse(ringPen, cx - r, cy - r, r * 2, r * 2);

        if (Failed)
        {
            using var xPen = new Pen(Color.FromArgb((int)(255 * _progress), Color.White), 3f);
            g.DrawLine(xPen, cx - 12, cy - 12, cx + 12, cy + 12);
            g.DrawLine(xPen, cx + 12, cy - 12, cx - 12, cy + 12);
            return;
        }

        if (_progress <= 0) return;
        using var checkPen = new Pen(Color.FromArgb((int)(255 * _progress), Color.White), 3.5f)
        {
            StartCap = LineCap.Round,
            EndCap = LineCap.Round,
        };
        var t = Math.Min(1f, _progress * 1.4f);
        if (t > 0)
        {
            var p1 = new Point(cx - 14, cy + 2);
            var p2 = new Point(cx - 4, cy + 12);
            var p3 = new Point(cx + 16, cy - 10);
            if (t < 0.5f)
                g.DrawLine(checkPen, p1, Lerp(p1, p2, t * 2));
            else
                g.DrawLine(checkPen, p1, p2);
            if (t > 0.5f)
                g.DrawLine(checkPen, p2, Lerp(p2, p3, (t - 0.5f) * 2));
        }
    }

    static Point Lerp(Point a, Point b, float t) =>
        new((int)(a.X + (b.X - a.X) * t), (int)(a.Y + (b.Y - a.Y) * t));
}
