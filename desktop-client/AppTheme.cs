namespace AITeamRoom;

internal static class AppTheme
{
    public static readonly Color Bg = Color.FromArgb(10, 11, 16);
    public static readonly Color Surface = Color.FromArgb(18, 20, 28);
    public static readonly Color Surface2 = Color.FromArgb(24, 27, 38);
    public static readonly Color Border = Color.FromArgb(28, 255, 255, 255);
    public static readonly Color Text = Color.FromArgb(242, 243, 247);
    public static readonly Color Muted = Color.FromArgb(148, 150, 168);
    public static readonly Color Accent = Color.FromArgb(139, 92, 246);
    public static readonly Color Accent2 = Color.FromArgb(122, 162, 255);
    public static readonly Color Gold = Color.FromArgb(196, 165, 116);
    public static readonly Color Success = Color.FromArgb(94, 207, 138);
    public static readonly Color Danger = Color.FromArgb(255, 71, 87);

    public static readonly Font FontUi = new("Segoe UI", 9F, FontStyle.Regular, GraphicsUnit.Point);
    public static readonly Font FontTitle = new("Segoe UI Semibold", 11F, FontStyle.Bold, GraphicsUnit.Point);
    public static readonly Font FontHead = new("Segoe UI", 18F, FontStyle.Bold, GraphicsUnit.Point);

    public static void StylePrimaryButton(Button btn)
    {
        btn.FlatStyle = FlatStyle.Flat;
        btn.FlatAppearance.BorderSize = 0;
        btn.BackColor = Accent;
        btn.ForeColor = Color.White;
        btn.Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold);
        btn.Cursor = Cursors.Hand;
        btn.Padding = new Padding(12, 4, 12, 4);
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
        tb.Font = FontUi;
    }

    public static void PaintGradientAccent(Graphics g, Rectangle bounds)
    {
        using var brush = new LinearGradientBrush(
            bounds,
            Accent,
            Accent2,
            LinearGradientMode.Horizontal);
        g.FillRectangle(brush, bounds);
    }
}
