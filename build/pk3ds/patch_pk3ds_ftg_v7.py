from pathlib import Path

ROOT = Path('src')

def replace_once(path, old, new, label):
    p = ROOT / path
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise SystemExit(f'PATCH FAILED [{label}]: anchor not found in {path}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')
    print('patched', label)

# --- UI: repurpose the old No Mega toggle into the FTG Mega progression toggle. ---
form = 'pk3DS.WinForms/Subforms/UniversalRandomizerForm.cs'
replace_once(form,
    'this.Text = "Universal Pokemon Randomizer ZX v4.6.1";',
    'this.Text = "Universal Pokemon Randomizer ZX - FTG v7";',
    'window title')

replace_once(form,
    'CHK_TrainerNoMegaEvolution = new CheckBox { Text = "No Mega Evolution", Location = new Point(580, 218), AutoSize = true };',
    'CHK_TrainerNoMegaEvolution = new CheckBox { Text = "Megas from Lv35+", Location = new Point(580, 218), AutoSize = true, Checked = true };',
    'mega UI label')

replace_once(form,
    'NoMegaEvolution = CHK_TrainerNoMegaEvolution.Checked,',
    'NoMegaEvolution = !CHK_TrainerNoMegaEvolution.Checked,',
    'mega UI save semantics')

replace_once(form,
    'CHK_TrainerNoMegaEvolution.Checked = s.NoMegaEvolution;',
    'CHK_TrainerNoMegaEvolution.Checked = !s.NoMegaEvolution;',
    'mega UI load semantics')

# --- Core randomizer: competitive mode no longer replaces shops with curated competitive shops. ---
core = 'pk3DS.Core/Randomizers/UniversalRandomizer.cs'
replace_once(core,
'''            if (Settings.CompetitiveRandomizer || Settings.RandomizeAllShops)
            {
                martRand.ExecuteCompetitive(Config.Info.MaxItemID, Config);

                // Expansion failing is not fatal - the shops are still filled - but it changes what
                // was asked for, so it is said out loud rather than left to be noticed in game.
                if (!string.IsNullOrEmpty(MartRandomizer.ExpansionSkipped))
                    progressCallback?.Invoke("WARNING: " + MartRandomizer.ExpansionSkipped, 95);
            }
            else
                martRand.Execute(Config.Info.MaxItemID);''',
'''            // FTG: shop randomization is independent from Competitive Mode.
            // Competitive teams should not turn every mart into a curated Showdown shop.
            // If the player asks to randomize shops, use the normal/random shop pool instead.
            martRand.Execute(Config.Info.MaxItemID);''',
    'decouple competitive shops')

# Mega rules also need the trainer pass when teams themselves are otherwise unchanged.
replace_once(core,
    'if (Settings.TrainerPokemonMode > 0 || Settings.TrainerLevelModifierPercent != 0)',
    'if (Settings.TrainerPokemonMode > 0 || Settings.TrainerLevelModifierPercent != 0 || !Settings.NoMegaEvolution)',
    'trainer pass for Mega35')

# Stop the competitive item engine from independently handing out Mega Stones; FTG assigns exactly one itself.
replace_once(core,
    'bool assignedMega = Settings.NoMegaEvolution;',
    'bool assignedMega = true; // FTG owns Mega assignment: none before Lv35, exactly one from Lv35 onward.',
    'suppress automatic competitive megas')

# Decide whether this trainer is in the Mega era, and reserve the ace slot.
replace_once(core,
'''                            trainer.NumPokemon = trainer.Pokemon.Count;
                        }

                        // 2. Generate Archetype & Roles for full team''',
'''                            trainer.NumPokemon = trainer.Pokemon.Count;
                        }

                        // FTG Mega progression: once the trainer's ace reaches Lv35, this battle gets
                        // exactly one Mega. The ace slot is reserved before builds/items are generated,
                        // so any species replacement still receives a coherent moveset and item.
                        int ProjectedLevel(TrainerPoke7 p)
                        {
                            if (Settings.TrainerLevelModifierPercent == 0) return p.Level;
                            return Math.Clamp((int)(p.Level * (1 + Settings.TrainerLevelModifierPercent / 100m)), 1, 100);
                        }

                        bool forceMegaTeam = false;
                        int forcedMegaSlot = -1;
                        if (!Settings.NoMegaEvolution && !isTutorialBattle && trainer.Pokemon.Count > 0)
                        {
                            var ace = trainer.Pokemon
                                .Select((p, idx) => (Level: ProjectedLevel(p), Index: idx))
                                .OrderByDescending(z => z.Level)
                                .ThenBy(z => z.Index)
                                .First();
                            forceMegaTeam = ace.Level >= FTGForcedMegaLevel;
                            if (forceMegaTeam) forcedMegaSlot = ace.Index;
                        }

                        // 2. Generate Archetype & Roles for full team''',
    'compute Mega35 eligibility')

# Make the reserved ace Mega-capable after species randomization/level adjustments, before build generation.
replace_once(core,
'''                            if (Settings.TrainerLevelModifierPercent != 0)
                                pk.Level = (byte)Math.Min(100, (int)Math.Max(1, pk.Level * (1 + (Settings.TrainerLevelModifierPercent / 100m))));

                            if (Settings.TrainerRandomShiny)''',
'''                            if (Settings.TrainerLevelModifierPercent != 0)
                                pk.Level = (byte)Math.Min(100, (int)Math.Max(1, pk.Level * (1 + (Settings.TrainerLevelModifierPercent / 100m))));

                            if (forceMegaTeam && pkIdx == forcedMegaSlot)
                                pk.Species = (ushort)PickFTGMegaSpecies(pk.Species, itemNames, Settings.TrainerDontUseLegendaries);

                            if (Settings.TrainerRandomShiny)''',
    'force Mega-capable ace species')

# Competitive builds: force the correct stone on the reserved ace; other slots still get smart items.
replace_once(core,
'''                                pk.Item = (int)buildEngine.AssignItem(pk.Species, pi, abilName, pk.Moves, role, itemNames, moveNames, Config.Moves, ref assignedMega, ref assignedZCrystal, archetype, teamAbilitiesCovered);

                                string heldItemName''',
'''                                if (forceMegaTeam && pkIdx == forcedMegaSlot)
                                {
                                    bool forcedMegaAssigned = false;
                                    ushort megaStone = buildEngine.TryAssignMegaStone(pk.Species, itemNames, ref forcedMegaAssigned);
                                    pk.Item = megaStone;
                                }
                                else
                                {
                                    pk.Item = (int)buildEngine.AssignItem(pk.Species, pi, abilName, pk.Moves, role, itemNames, moveNames, Config.Moves, ref assignedMega, ref assignedZCrystal, archetype, teamAbilitiesCovered);
                                }

                                string heldItemName''',
    'competitive forced mega item')

# Regular builds: same Mega guarantee, without enabling the full competitive team generator.
replace_once(core,
'''                                if (Settings.BetterTrainerMovesets)
                                    pk.Moves = moveRand.GetRandomMoveset(pk.Species);
                                if (shouldAddHeldItems && (pk.Item == 0 || Settings.WildRandomizeHeldItems))
                                    pk.Item = sensibleItems[Util.Random32() % sensibleItems.Length];

                                Competitive.CompetitiveValidator.ValidateAndSanitize(''',
'''                                if (Settings.BetterTrainerMovesets)
                                    pk.Moves = moveRand.GetRandomMoveset(pk.Species);

                                if (forceMegaTeam && pkIdx == forcedMegaSlot)
                                {
                                    bool forcedMegaAssigned = false;
                                    ushort megaStone = buildEngine.TryAssignMegaStone(pk.Species, itemNames, ref forcedMegaAssigned);
                                    if (megaStone > 0) pk.Item = megaStone;
                                }
                                else if (shouldAddHeldItems && (pk.Item == 0 || Settings.WildRandomizeHeldItems))
                                {
                                    pk.Item = sensibleItems[Util.Random32() % sensibleItems.Length];
                                }

                                Competitive.CompetitiveValidator.ValidateAndSanitize(''',
    'regular forced mega item')

# Enforce EXACTLY one Mega Stone: strip stones from every non-ace slot and all pre-Lv35 teams.
replace_once(core,
'''                            // Recorded at the end, using whatever the slot finally settled on - the
                            // competitive path above can still change it after the initial pick.''',
'''                            // FTG Mega rule is strict: no stones before Lv35, and never more than one
                            // stone once the Mega era starts. This also cleans any stone inherited from
                            // the original trainer data.
                            if (pk.Item > 0 && pk.Item < itemNames.Length &&
                                (!forceMegaTeam || pkIdx != forcedMegaSlot) &&
                                Competitive.CompetitiveValidator.IsMegaStone(itemNames[pk.Item]))
                            {
                                pk.Item = 0;
                            }

                            // Recorded at the end, using whatever the slot finally settled on - the
                            // competitive path above can still change it after the initial pick.''',
    'strip extra/pre35 mega stones')

# Add constants/helper methods immediately before the existing FirstRivalBattle helper section.
anchor = '''    /// <summary>Whether a trainer is on the game's important-trainer list.</summary>
    private static bool IsImportantTrainer(int index) => TrainerTiers.IsImportant(index);'''
helper = '''    // FTG progression rule. The checkbox shown as "Megas from Lv35+" stores its inverse in
    // NoMegaEvolution so old settings strings remain compatible with this build.
    private const int FTGForcedMegaLevel = 35;

    // Mega-capable legendary/mythical species in the Expansion database. When the trainer option
    // "Don't Use Legendaries" is enabled, the forced ace is chosen from the remaining Mega pool.
    private static readonly HashSet<int> FTGLegendaryMegaSpecies =
        [150, 380, 381, 384, 485, 491, 718, 719, 801, 807];

    /// <summary>
    /// Keeps an already-valid Mega ace; otherwise replaces it with a Mega-capable species whose
    /// base-stat total is close to the slot it replaces. Only species with an actual stone present
    /// in the loaded ROM are candidates, which keeps this safe for the Expansion Mod's custom set.
    /// </summary>
    private int PickFTGMegaSpecies(int currentSpecies, string[] itemNames, bool avoidLegendaries)
    {
        bool StoneExists(string stone) => itemNames != null &&
            Array.FindIndex(itemNames, z => Competitive.GameNameComparer.Instance.Equals(z, stone)) > 0;

        bool Allowed(int species)
        {
            if (species <= 0 || Config?.Personal?.Table == null || species >= Config.Personal.Table.Length)
                return false;
            if (avoidLegendaries && FTGLegendaryMegaSpecies.Contains(species))
                return false;
            return Competitive.CompetitiveDatabase.MegaStoneMap.TryGetValue(species, out var stones) &&
                   stones.Any(StoneExists);
        }

        if (Allowed(currentSpecies))
            return currentSpecies;

        var candidates = Competitive.CompetitiveDatabase.MegaStoneMap.Keys
            .Where(Allowed)
            .ToList();
        if (candidates.Count == 0)
            return currentSpecies;

        int targetBST = currentSpecies > 0 && currentSpecies < Config.Personal.Table.Length
            ? Config.Personal.Table[currentSpecies]?.BST ?? 500
            : 500;

        // Pick randomly from the closest few rather than always selecting the exact same species
        // for a given BST. This keeps the RandomLocke feel while avoiding absurd power jumps.
        var shortlist = candidates
            .OrderBy(s => Math.Abs((Config.Personal.Table[s]?.BST ?? targetBST) - targetBST))
            .ThenBy(_ => Util.Rand.Next())
            .Take(Math.Min(8, candidates.Count))
            .ToArray();

        return shortlist[Util.Rand.Next(shortlist.Length)];
    }

    /// <summary>Whether a trainer is on the game's important-trainer list.</summary>
    private static bool IsImportantTrainer(int index) => TrainerTiers.IsImportant(index);'''
replace_once(core, anchor, helper, 'Mega35 helper methods')

print('FTG v7 patch completed successfully.')
