from pathlib import Path

ROOT = Path('src')


def replace_once(path, old, new, label):
    p = ROOT / path
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'PATCH FAILED [{label}]: anchor not found in {path}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print('patched', label)

# Version label.
form = 'pk3DS.WinForms/Subforms/UniversalRandomizerForm.cs'
replace_once(
    form,
    'this.Text = "Universal Pokemon Randomizer ZX - FTG v7";',
    'this.Text = "Universal Pokemon Randomizer ZX - FTG v7.1";',
    'window title v7.1',
)

# FTG FIX: do not infer Ultra Sun / Ultra Moon from the folder name.
# GameConfig already knows the actual version from the loaded GARCs via UltraSun/UltraMoon.
# LayeredFS folders are named with the Title ID, so the old path-only resolver defaulted to UM.
rv = 'pk3DS.Core/Modding/Research/ResearchVersion.cs'
replace_once(
    rv,
'''        // Sun/Moon are a different generation of the corpus entirely.
        if (cfg?.SM == true) return "SM";

        string hint = (romfsPath ?? "") + " " + (cfg?.RomFS ?? "");''',
'''        // Sun/Moon are a different generation of the corpus entirely.
        if (cfg?.SM == true) return "SM";

        // FTG: trust the loaded game data before looking at folder names. LayeredFS paths such as
        // 00040000001B5000/romfs contain no "UltraSun" token, so the old resolver incorrectly
        // fell through to the UM default even when GameConfig had already identified Ultra Sun.
        if (cfg?.UltraSun == true) return "US";
        if (cfg?.UltraMoon == true) return "UM";

        string hint = (romfsPath ?? "") + " " + (cfg?.RomFS ?? "");''',
    'reliable US/UM detection',
)

print('FTG v7.1 patch completed successfully.')
