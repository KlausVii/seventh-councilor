#!/usr/bin/env python3
"""Generate Ship Modules/ comparison tables and inject inline stats into project files."""
import json
import re
from collections import defaultdict
from pathlib import Path

from ti_config import find_templates_dir, find_localization_dir

ROOT = Path(__file__).resolve().parent.parent / "generated"
_templates_dir = find_templates_dir()
_localization_dir = find_localization_dir()
if _templates_dir is None or _localization_dir is None:
    raise SystemExit(
        "Game templates/localization not found. Run sync_game_data.py first, "
        'or set "game_install_dir" in config.json.'
    )
TEMPLATES = Path(_templates_dir)
LOCAL = Path(_localization_dir)

# ---------- helpers ----------
def parse_localization(path: Path) -> dict:
    result = {}
    if not path.exists():
        return result
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if text.startswith("﻿"):
        text = text[1:]
    cur_key = None
    cur_val_lines = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        cm = re.search(r"\s+//(?!/)(.*)$", line)
        if cm and "://" not in line[:cm.start()]:
            line = line[:cm.start()].rstrip()
        if "=" in line and re.match(r"^[A-Za-z][\w.\-]*=", line):
            if cur_key is not None:
                result[cur_key] = "\n".join(cur_val_lines).rstrip()
            k, _, v = line.partition("=")
            cur_key = k.strip()
            cur_val_lines = [v]
        else:
            if cur_key is not None:
                cur_val_lines.append(line)
    if cur_key is not None:
        result[cur_key] = "\n".join(cur_val_lines).rstrip()
    return result

def fmt(x, suffix="", decimals=None):
    if x is None or x == "":
        return ""
    try:
        v = float(x)
        if v == int(v) and decimals is None:
            return f"{int(v):,}{suffix}"
        if decimals is not None:
            return f"{v:,.{decimals}f}{suffix}"
        return f"{v:g}{suffix}"
    except Exception:
        return f"{x}{suffix}"

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

# ---------- load templates ----------
def load(name):
    """Load a template JSON and resolve each entry's in-game display name from
    the matching localization file (standing directive 2026-07-07: in-game
    names, not template friendlyNames — ~300 module names differ)."""
    data = json.loads((TEMPLATES / f"{name}.json").read_text(encoding="utf-8"))
    loc = parse_localization(LOCAL / f"{name}.en")
    for e in data:
        d = loc.get(f"{name}.displayName.{e.get('dataName', '')}")
        if d:
            e["_localizedName"] = d
    return data

magnetic_guns = load("TIMagneticGunTemplate")
lasers = load("TILaserWeaponTemplate")
plasma = load("TIPlasmaWeaponTemplate")
particle = load("TIParticleWeaponTemplate")
guns = load("TIGunTemplate")
missiles = load("TIMissileTemplate")
drives = load("TIDriveTemplate")
power = load("TIPowerPlantTemplate")
habs = load("TIHabModuleTemplate")
utility = load("TIUtilityModuleTemplate")
hulls = load("TIShipHullTemplate")
armor = load("TIShipArmorTemplate")
radiators = load("TIRadiatorTemplate")
batteries = load("TIBatteryTemplate")
heatsinks = load("TIHeatSinkTemplate")

# ---------- display-name resolution ----------
# Prefer the in-game localized name (resolved in load()); fall back to the
# template's own friendlyName/displayName fields, then the dataName.
def name_of(entry):
    if entry.get("_localizedName"):
        return entry["_localizedName"]
    if entry.get("friendlyName"):
        return entry["friendlyName"]
    if entry.get("displayName"):
        return entry["displayName"]
    return entry["dataName"]

# Build map: project dataName -> list of (category, friendly_name, stats_summary_lines)
project_to_modules = defaultdict(list)

# ---------- inline summary builders ----------
def mat_str(d):
    if not d: return ""
    parts = [f"{k} {v*100:.0f}%" for k, v in d.items() if v]
    return " · ".join(parts)

def fmt_mount(m):
    """OneNose -> One Nose, TwoNoseVert -> Two Nose Vert."""
    if not m: return ""
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", m)
    return s

def magnetic_gun_summary(e):
    return [
        f"Mount: {fmt_mount(e.get('mount'))} · Mass: {fmt(e.get('baseWeaponMass_tons'),' t')} · Crew: {e.get('crew',0)}",
        f"Cooldown {fmt(e.get('cooldown_s'),' s')} · Salvo {e.get('salvo_shots',1)} shot(s) @ {fmt(e.get('intraSalvoCooldown_s'),' s')} · Magazine {e.get('magazine','—')}",
        f"Muzzle vel {fmt(e.get('muzzleVelocity_kps'),' km/s')} · Warhead {fmt(e.get('warheadMass_kg'),' kg')} · Range {fmt(e.get('targetingRange_km'),' km')} · Bombardment {e.get('bombardmentValue',0)}",
        f"Efficiency {fmt(e.get('efficiency'))} · Chipping {fmt(e.get('flatChipping'))} · Pivot {fmt(e.get('pivotRange_deg'),'°')} · Point-defenseable: {'yes' if e.get('isPointDefenseTargetable') else 'no'}",
    ]

def laser_summary(e):
    return [
        f"Mount: {fmt_mount(e.get('mount'))} · Mass: {fmt(e.get('baseWeaponMass_tons'),' t')} · Crew: {e.get('crew',0)}",
        f"Shot power {fmt(e.get('shotPower_MJ'),' MJ')} · Cooldown {fmt(e.get('cooldown_s'),' s')} · Efficiency {fmt(e.get('efficiency'))}",
        f"Mirror Ø {fmt(e.get('mirrorRadius_cm'),' cm')} · Wavelength {fmt(e.get('wavelength_nm'),' nm')} · Beam quality {fmt(e.get('beam_quality'))} · Jitter {fmt(e.get('jitter_Rad'))} rad",
        f"Range {fmt(e.get('targetingRange_km'),' km')} · Bombardment {e.get('bombardmentValue',0)} · Pivot {fmt(e.get('pivotRange_deg'),'°')} · Point-defenseable: {'yes' if e.get('isPointDefenseTargetable') else 'no'}",
    ]

def plasma_summary(e):
    return [
        f"Mount: {fmt_mount(e.get('mount'))} · Mass: {fmt(e.get('baseWeaponMass_tons'),' t')} · Crew: {e.get('crew',0)}",
        f"Charge {fmt(e.get('chargingEnergy_GJ'),' GJ')} · Cooldown {fmt(e.get('cooldown_s'),' s')} · Magazine {e.get('magazine','—')}",
        f"Damage {fmt(e.get('expectedDamage_MJ'),' MJ')} · Muzzle vel {fmt(e.get('muzzleVelocity_kps'),' km/s')} · Warhead {fmt(e.get('warheadMass_kg'),' kg')} · Range {fmt(e.get('targetingRange_km'),' km')}",
        f"Efficiency {fmt(e.get('efficiency'))} · Chipping {fmt(e.get('flatChipping'))} · Pivot {fmt(e.get('pivotRange_deg'),'°')}",
        (f"Build materials: {mat_str(e.get('weightedBuildMaterials'))}" if e.get('weightedBuildMaterials') else None),
    ]

def particle_summary(e):
    return [
        f"Mount: {fmt_mount(e.get('mount'))} · Mass: {fmt(e.get('baseWeaponMass_tons'),' t')} · Crew: {e.get('crew',0)}",
        f"Shot {fmt(e.get('shotPower_MJ'),' MJ')} · Salvo {e.get('salvo_shots',1)} @ {fmt(e.get('intraSalvoCooldown_s'),' s')} · Cooldown {fmt(e.get('cooldown_s'),' s')} · Efficiency {fmt(e.get('efficiency'))}",
        f"Lens Ø {fmt(e.get('lensRadius_cm'),' cm')} · Dispersion: {e.get('dispersionModel','—')} · Emittance {fmt(e.get('emittance_mrad'),' mrad')}",
        f"Heat {fmt((e.get('heatFraction') or 0)*100,'%')} · X-ray {fmt((e.get('xRayFraction') or 0)*100,'%')} · Baryon {fmt((e.get('baryonFraction') or 0)*100,'%')} · Range {fmt(e.get('targetingRange_km'),' km')}",
    ]

def gun_summary(e):
    return [
        f"Mount: {fmt_mount(e.get('mount'))} · Mass: {fmt(e.get('baseWeaponMass_tons'),' t')} · Crew: {e.get('crew',0)}",
        f"Cooldown {fmt(e.get('cooldown_s'),' s')} · Salvo {e.get('salvo_shots',1)} shot(s) @ {fmt(e.get('intraSalvoCooldown_s'),' s')} · Magazine {e.get('magazine','—')}",
        f"Damage {fmt(e.get('damage_MJ'),' MJ')} · Muzzle vel {fmt(e.get('muzzleVelocity_kps'),' km/s')} · Warhead {fmt(e.get('warheadMass_kg'),' kg')} · Range {fmt(e.get('targetingRange_km'),' km')}",
    ]

def missile_summary(e):
    return [
        f"Mount: {fmt_mount(e.get('mount'))} · Mass: {fmt(e.get('baseWeaponMass_tons'),' t')} · Crew: {e.get('crew',0)} · Magazine {e.get('magazine','—')}",
        f"Warhead class: {e.get('warheadClass','—')} · Damage {fmt(e.get('flatDamage_MJ'),' MJ')} · Bombardment {e.get('bombardmentValue',0)}",
        f"ΔV {fmt(e.get('deltaV_kps'),' km/s')} · Accel {fmt(e.get('acceleration_g'),' g')} · Thrust {fmt(e.get('Rocket Thrust'),' N')} · EV {fmt(e.get('EV_kps'),' km/s')}",
        f"Cooldown {fmt(e.get('cooldown_s'),' s')} · Range {fmt(e.get('targetingRange_km'),' km')} · Maneuver {e.get('maneuver_angle','—')}° · Rotation {fmt(e.get('rotation_degps'),' °/s')}",
    ]

def drive_summary(e):
    return [
        f"Class: {e.get('driveClassification','—')} · Propellant: {e.get('propellant','—')} · Power plant: {e.get('requiredPowerPlant','—')}",
        f"Thrust {fmt(e.get('thrust_N'),' N')} · EV (ISP) {fmt(e.get('EV_kps'),' km/s')} · Efficiency {fmt(e.get('efficiency'))}",
        f"Thrust rating {e.get('thrustRating_GW','—')} GW · Required power {e.get('req power','—')} GW · Cooling: {e.get('cooling','—')}",
        f"Thrusters: {e.get('thrusters','?')} · Cap: {e.get('thrustCap','—')} · Specific power {fmt(e.get('specificPower_kgMW'),' kg/MW')} · Notes: {e.get('notes','')}",
    ]

def power_summary(e):
    return [
        f"Class: {e.get('powerPlantClass','—')} · Output: {fmt(e.get('maxOutput_GW'),' GW')} · Efficiency {fmt(e.get('efficiency'))}",
        f"Specific power: {fmt(e.get('specificPower_tGW'),' t/GW')} · Crew: {e.get('crew',0)}",
    ]

def hab_summary(e):
    flags = []
    for k in ("coreModule","onePerHab","automated","allowsShipConstruction","allowsResupply","mine","alienModule"):
        if e.get(k): flags.append(k.replace('_',' '))
    incomes = []
    for k, v in e.items():
        if k.startswith("income") and v:
            res = k.replace("income","").replace("_month","")
            incomes.append(f"{res} +{v}/mo")
    sp = e.get("specialRules") or []
    return [
        f"Type: {e.get('habType','Any')} · Tier {e.get('tier','—')} · Mass: {fmt(e.get('baseMass_tons'),' t')} · Crew: {e.get('crew',0)} · Power: {e.get('power',0)} MW",
        f"Build: {e.get('buildTime_Days',0)} days · CP cap: {e.get('controlPointCapacity',0)} · Mission control: {e.get('missionControl',0)}",
        ("Income: " + " · ".join(incomes)) if incomes else None,
        ("Flags: " + " · ".join(flags)) if flags else None,
        ("Special: " + ", ".join(sp)) if sp else None,
    ]

def utility_summary(e):
    sp = e.get("specialModuleRules") or []
    return [
        f"Mass: {fmt(e.get('mass_tons'),' t')} · Crew: {e.get('crew',0)} · Power: {fmt(e.get('powerRequirement_MW'),' MW')} · Cons. tier ≥ {e.get('minConsTier',0)}",
        ("Special: " + ", ".join(sp)) if sp else None,
    ]

def hull_summary(e):
    return [
        f"Cons. tier: {e.get('consTier','—')} · Length {fmt(e.get('length_m'),' m')} · Mass: {fmt(e.get('mass_tons'),' t')} · Crew: {e.get('crew',0)} · Officers: {e.get('maxOfficers',0)}",
        f"Hardpoints — Nose: {e.get('noseHardpoints',0)} · Hull: {e.get('hullHardpoints',0)} · Internal modules: {e.get('internalModules',0)}",
        f"Mission control: {e.get('missionControl',0)} · Structural integrity: {e.get('structuralIntegrity','—')} · Build: {e.get('baseConstructionTime_days',0)} days · Income: {e.get('monthlyIncome_Money',0)} $/mo",
    ]

def armor_summary(e):
    sp = e.get("specialties") or []
    sp_str = ", ".join(f"{s.get('armorSpecialty','?')}={s.get('value',0)}" for s in sp if s.get('armorSpecialty') and s.get('armorSpecialty')!='None')
    return [
        f"Density {fmt(e.get('density_kgm3'),' kg/m³')} · Heat of vaporization {fmt(e.get('heatofVaporization_MJkg'),' MJ/kg')}",
        f"X-ray HV: {fmt(e.get('xRayHalfValue_cm'),' cm')} · Baryonic HV: {fmt(e.get('baryonicHalfValue_cm'),' cm')}",
        ("Specialties: " + sp_str) if sp_str else None,
    ]

def rad_summary(e):
    return [
        f"Type: {e.get('radiatorType','—')} · Operating temp {fmt(e.get('operatingTemp_K'),' K')} · Emissivity {fmt(e.get('emissivity'))}",
        f"Specific power {fmt(e.get('specificPower_2s_KWkg'),' kW/kg')} · Specific mass {fmt(e.get('specificMass_2s_kgm2'),' kg/m²')} · Vulnerability {fmt(e.get('vulnerability'))} · Crew {e.get('crew',0)}",
    ]

def battery_summary(e):
    return [
        f"Capacity {fmt(e.get('energyCapacity_GJ'),' GJ')} · Recharge {fmt(e.get('rechargeRate_GJs'),' GJ/s')} · Mass {fmt(e.get('mass_tons'),' t')} · HP {e.get('hp','—')}",
    ]

def heatsink_summary(e):
    return [
        f"Capacity {fmt(e.get('heatCapacity_GJ'),' GJ')} · Mass {fmt(e.get('mass_tons'),' t')} · Crew {e.get('crew',0)}",
    ]

# ---------- collate per-project module summaries ----------
def attach(template_list, kind_label, summary_fn, dedup_drives=False):
    if dedup_drives:
        # Drives: many thruster-count variants per project. Take x1 as representative.
        seen = set()
        for e in sorted(template_list, key=lambda x: x.get("thrusters",1) or 1):
            proj = e.get("requiredProjectName")
            if not proj: continue
            if proj in seen: continue
            seen.add(proj)
            display = name_of(e)
            # Replace "x1" suffix in displayed name
            display = re.sub(r"\s*x\d+\s*$", "", display).strip()
            summary = [l for l in summary_fn(e) if l]
            project_to_modules[proj].append((kind_label, display, summary))
    else:
        for e in template_list:
            proj = e.get("requiredProjectName")
            if not proj: continue
            display = name_of(e)
            summary = [l for l in summary_fn(e) if l]
            project_to_modules[proj].append((kind_label, display, summary))

attach(magnetic_guns, "Magnetic Gun", magnetic_gun_summary)
attach(lasers, "Laser", laser_summary)
attach(plasma, "Plasma Weapon", plasma_summary)
attach(particle, "Particle Beam", particle_summary)
attach(guns, "Conventional Gun", gun_summary)
attach(missiles, "Missile", missile_summary)
attach(drives, "Drive", drive_summary, dedup_drives=True)
attach(power, "Power Plant", power_summary)
attach(habs, "Habitat Module", hab_summary)
attach(utility, "Utility Module", utility_summary)
attach(hulls, "Ship Hull", hull_summary)
attach(armor, "Armor", armor_summary)
attach(radiators, "Radiator", rad_summary)
attach(batteries, "Battery", battery_summary)
attach(heatsinks, "Heat Sink", heatsink_summary)

print(f"Modules collated for {len(project_to_modules)} projects.")

# ---------- inject into project files ----------
def project_data_name_to_path(dn):
    """Find the .md file for a given project dataName by scanning frontmatter."""
    return _project_path_index.get(dn)

# Build path index
_project_path_index = {}
for md in ROOT.rglob("*.md"):
    if "Tech Tree" not in md.parts: continue  # os.sep-agnostic (Windows uses backslashes)
    try:
        text = md.read_text(encoding="utf-8")
    except Exception:
        continue
    m = re.search(r"^data_name:\s*(\S+)\s*$", text, re.MULTILINE)
    if m:
        _project_path_index[m.group(1)] = md

print(f"Path index has {len(_project_path_index)} project files.")

INJECTION_HEADER = "## Ship modules unlocked"

KIND_TO_MOC = {
    "Magnetic Gun":     "Magnetic Guns",
    "Laser":            "Lasers",
    "Plasma Weapon":    "Plasma Weapons",
    "Particle Beam":    "Particle Weapons",
    "Conventional Gun": "Conventional Guns",
    "Missile":          "Missiles",
    "Drive":            "Drives",
    "Power Plant":      "Power Plants",
    "Habitat Module":   "Habitat Modules",
    "Utility Module":   "Utility Modules",
    "Ship Hull":        "Ship Hulls",
    "Armor":            "Armor",
    "Radiator":         "Radiators",
    "Battery":          "Batteries",
    "Heat Sink":        "Heat Sinks",
}

def render_modules_block(modules):
    lines = [INJECTION_HEADER, ""]
    # One-line summary of which comparison MOCs apply to this project, in display order
    seen_kinds = []
    for kind, _, _ in modules:
        if kind not in seen_kinds:
            seen_kinds.append(kind)
    if seen_kinds:
        moc_links = " · ".join(f"[[{KIND_TO_MOC[k]}]]" for k in seen_kinds if k in KIND_TO_MOC)
        if moc_links:
            lines.append(f"_Compare against all entries: {moc_links}._")
            lines.append("")
    for kind, name, summary in modules:
        moc = KIND_TO_MOC.get(kind, kind)
        lines.append(f"### {name}  _([[{moc}|{kind}]])_")
        for s in summary:
            lines.append(f"- {s}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

n_injected = 0
for proj, modules in project_to_modules.items():
    md = project_data_name_to_path(proj)
    if not md:
        continue
    text = md.read_text(encoding="utf-8")
    block = render_modules_block(modules)
    # Replace existing block if present (idempotent), else inject before "## Effects"
    pattern = re.compile(r"## Ship modules unlocked\n.*?(?=\n## |\n---\n\*Data name)", re.DOTALL)
    if pattern.search(text):
        new_text = pattern.sub(block.rstrip() + "\n\n", text, count=1)
    else:
        # Insert before "## Effects"
        if "## Effects" in text:
            new_text = text.replace("## Effects", block + "\n## Effects", 1)
        else:
            # Append before final --- footer
            new_text = re.sub(r"(\n---\n\*Data name:)", f"\n{block}\n\\1", text, count=1)
    if new_text != text:
        md.write_text(new_text, encoding="utf-8")
        n_injected += 1
print(f"Injected module sections into {n_injected} project files.")

# ---------- generate Ship Modules comparison MOCs ----------
def link_project(p):
    if not p: return ""
    # Use shortest unique name = friendlyName, which we don't directly have here; rely on dataName lookup
    md = project_data_name_to_path(p)
    if md:
        # filename without .md = friendly name
        return f"[[{md.stem}]]"
    return f"`{p}`"

def fmt_cell(x, decimals=None, suffix=""):
    if x is None or x == "":
        return ""
    try:
        v = float(x)
        if decimals is None:
            if v == int(v):
                return f"{int(v):,}{suffix}"
            return f"{v:g}{suffix}"
        return f"{v:,.{decimals}f}{suffix}"
    except Exception:
        return f"{x}{suffix}"

def write_comparison(filename, title, intro, headers, rows, sort_key=None):
    if sort_key:
        rows = sorted(rows, key=sort_key)
    lines = [
        "---",
        f"name: {title}",
        "type: reference",
        "tags:",
        "  - moc",
        "  - ship-modules",
        "---",
        "",
        f"# {title}",
        "",
        intro,
        "",
        f"**{len(rows)} entries**.",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for r in rows:
        cells = [str(c).replace("|", "\\|") if c is not None else "" for c in r]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    write(ROOT / "Ship Modules" / filename, "\n".join(lines))

# Magnetic guns
rows = []
for e in sorted(magnetic_guns, key=lambda x: (x.get("sort", 999), x.get("baseWeaponMass_tons", 0))):
    rows.append([
        f"[[{name_of(e)}]]" if False else name_of(e),  # plain name — modules don't have own files
        fmt_mount(e.get("mount")),
        fmt_cell(e.get("baseWeaponMass_tons")),
        e.get("crew",0),
        fmt_cell(e.get("cooldown_s")),
        e.get("salvo_shots",1),
        fmt_cell(e.get("intraSalvoCooldown_s")),
        e.get("magazine",""),
        fmt_cell(e.get("muzzleVelocity_kps")),
        fmt_cell(e.get("warheadMass_kg")),
        fmt_cell(e.get("targetingRange_km")),
        e.get("bombardmentValue",0),
        fmt_cell(e.get("flatChipping")),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Magnetic Guns.md", "Magnetic Guns",
    "Coil cannons, mass drivers, railguns. Damage scales with **muzzle velocity × warhead mass** (kinetic energy). High velocity penetrates armor; small warhead means mediocre crater. Magnetic guns are point-defenseable (slow shots can be intercepted) but very ammo-efficient.",
    ["Name","Mount","Mass (t)","Crew","CD (s)","Salvo","Intra (s)","Magazine","MV (km/s)","Warhead (kg)","Range (km)","Bombard","Chip","Project"],
    rows)

# Lasers
rows = []
for e in sorted(lasers, key=lambda x: (x.get("sortOrder", 999), x.get("baseWeaponMass_tons", 0))):
    rows.append([
        name_of(e),
        fmt_mount(e.get("mount")),
        fmt_cell(e.get("baseWeaponMass_tons")),
        e.get("crew",0),
        fmt_cell(e.get("cooldown_s")),
        fmt_cell(e.get("shotPower_MJ")),
        fmt_cell(e.get("efficiency")),
        fmt_cell(e.get("mirrorRadius_cm")),
        fmt_cell(e.get("wavelength_nm")),
        fmt_cell(e.get("beam_quality")),
        fmt_cell(e.get("jitter_Rad")),
        fmt_cell(e.get("targetingRange_km")),
        e.get("bombardmentValue",0),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Lasers.md", "Lasers",
    "Light-speed weapons with no muzzle-velocity travel time. Damage = `shotPower_MJ × efficiency × on-target fraction`. Smaller wavelength + larger mirror + lower jitter = tighter beam (more energy on target at range). Phasers are pulsed; particle-/X-ray-pumped graser variants beat regular lasers at long range.",
    ["Name","Mount","Mass (t)","Crew","CD (s)","Power (MJ)","Eff.","Mirror (cm)","λ (nm)","Beam Q","Jitter (rad)","Range (km)","Bombard","Project"],
    rows)

# Plasma weapons
rows = []
for e in sorted(plasma, key=lambda x: (x.get("sort", 999), x.get("baseWeaponMass_tons", 0))):
    rows.append([
        name_of(e),
        fmt_mount(e.get("mount")),
        fmt_cell(e.get("baseWeaponMass_tons")),
        e.get("crew",0),
        fmt_cell(e.get("cooldown_s")),
        fmt_cell(e.get("chargingEnergy_GJ")),
        fmt_cell(e.get("expectedDamage_MJ")),
        fmt_cell(e.get("muzzleVelocity_kps")),
        fmt_cell(e.get("warheadMass_kg")),
        e.get("magazine",""),
        fmt_cell(e.get("targetingRange_km")),
        fmt_cell(e.get("flatChipping")),
        mat_str(e.get("weightedBuildMaterials")),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Plasma Weapons.md", "Plasma Weapons",
    "Magnetically-confined plasma slugs. Slower than lasers but huge per-shot damage and excellent armor chipping. Charging energy is drawn from reactor/battery; magazine limits sustained fire.",
    ["Name","Mount","Mass (t)","Crew","CD (s)","Charge (GJ)","Damage (MJ)","MV (km/s)","Warhead (kg)","Mag","Range (km)","Chip","Build materials","Project"],
    rows)

# Particle weapons
rows = []
for e in particle:
    rows.append([
        name_of(e),
        fmt_mount(e.get("mount")),
        fmt_cell(e.get("baseWeaponMass_tons")),
        e.get("crew",0),
        fmt_cell(e.get("cooldown_s")),
        e.get("salvo_shots",1),
        fmt_cell(e.get("shotPower_MJ")),
        fmt_cell(e.get("efficiency")),
        fmt_cell(e.get("lensRadius_cm")),
        e.get("dispersionModel",""),
        fmt_cell(e.get("emittance_mrad")),
        fmt_cell(e.get("targetingRange_km")),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Particle Weapons.md", "Particle Weapons",
    "Beams of accelerated particles — neutral or charged. Charged particles disperse in magnetic fields (limited range), neutrals reach further. Damage from heat + X-ray + baryon fractions; very high single-shot energy but constrained by lens size and emittance.",
    ["Name","Mount","Mass (t)","Crew","CD (s)","Salvo","Shot (MJ)","Eff.","Lens (cm)","Disperse","Emit (mrad)","Range (km)","Project"],
    rows)

# Conventional guns
rows = []
for e in guns:
    rows.append([
        name_of(e),
        fmt_mount(e.get("mount")),
        fmt_cell(e.get("baseWeaponMass_tons")),
        e.get("crew",0),
        fmt_cell(e.get("cooldown_s")),
        e.get("salvo_shots",1),
        fmt_cell(e.get("damage_MJ")),
        fmt_cell(e.get("muzzleVelocity_kps")),
        fmt_cell(e.get("warheadMass_kg")),
        e.get("magazine",""),
        fmt_cell(e.get("targetingRange_km")),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Conventional Guns.md", "Conventional Guns",
    "Chemical-propellant cannons. Cheap, low-tech, low-energy, short range. Mostly relegated to point defense and atmospheric/low-orbit work after early-game.",
    ["Name","Mount","Mass (t)","Crew","CD (s)","Salvo","Damage (MJ)","MV (km/s)","Warhead (kg)","Mag","Range (km)","Project"],
    rows)

# Missiles
rows = []
for e in sorted(missiles, key=lambda x: x.get("baseWeaponMass_tons",0)):
    rows.append([
        name_of(e),
        fmt_mount(e.get("mount")),
        fmt_cell(e.get("baseWeaponMass_tons")),
        e.get("crew",0),
        e.get("warheadClass",""),
        fmt_cell(e.get("flatDamage_MJ")),
        e.get("bombardmentValue",0),
        fmt_cell(e.get("deltaV_kps")),
        fmt_cell(e.get("acceleration_g")),
        fmt_cell(e.get("EV_kps")),
        e.get("magazine",""),
        fmt_cell(e.get("cooldown_s")),
        fmt_cell(e.get("targetingRange_km")),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Missiles.md", "Missiles & Torpedoes",
    "Self-propelled munitions. ΔV decides if it can chase the target; acceleration decides if it dodges point defense. Nuclear and shaped-nuclear warheads scale to gigatons of MJ. Magazine is small (4–24); damage class > range.",
    ["Name","Mount","Mass (t)","Crew","Warhead","Damage (MJ)","Bombard","ΔV (km/s)","Accel (g)","EV (km/s)","Mag","CD (s)","Range (km)","Project"],
    rows)

# Drives — group by classification, dedupe by project
DRIVE_ORDER = ["Chemical","Electrothermal","Electrostatic","Electromagnetic","Fission_Thermal","Fission_Pulse","NuclearSaltWater","Fusion_Thermal","Antimatter"]
drive_by_proj = {}
for e in sorted(drives, key=lambda x: (x.get("thrusters",1) or 1)):
    p = e.get("requiredProjectName")
    if not p or p in drive_by_proj: continue
    drive_by_proj[p] = e
rows = []
def drive_class_rank(c): return DRIVE_ORDER.index(c) if c in DRIVE_ORDER else 99
for e in sorted(drive_by_proj.values(), key=lambda x: (drive_class_rank(x.get("driveClassification","?")), -float(x.get("EV_kps",0) or 0))):
    name = re.sub(r"\s*x\d+\s*$", "", name_of(e)).strip()
    rows.append([
        name,
        e.get("driveClassification","").replace("_"," "),
        e.get("propellant",""),
        fmt_cell(e.get("thrust_N")),
        fmt_cell(e.get("EV_kps")),
        fmt_cell(e.get("efficiency")),
        e.get("thrustRating_GW",""),
        e.get("req power",""),
        e.get("requiredPowerPlant","").replace("_"," "),
        e.get("cooling",""),
        e.get("thrustCap",""),
        e.get("notes",""),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Drives.md", "Drives",
    "One row per drive type (the per-thruster x1 stats). Multi-thruster variants scale thrust and req power roughly linearly while EV and efficiency stay constant. Higher EV (exhaust velocity / Isp equivalent) is more fuel-efficient; higher thrust accelerates faster. **Closed-cycle = self-cooled, Open = needs propellant flow.** Power plant must match the drive's `requiredPowerPlant`.",
    ["Name","Class","Propellant","Thrust (N)","EV (km/s)","Eff.","Rating (GW)","Req power (GW)","Power plant","Cooling","Cap","Notes","Project"],
    rows)

# Power Plants
POWER_ORDER = ["Solar_Thermal","Chemical_Combustion","Solid_Core_Fission","Gas_Core_Fission","Inertial_Confinement_Fusion","Magnetic_Confinement_Fusion","Mirrored_Magnetic_Confinement_Fusion","Z_Pinch_Fusion","Magnetoinertial_Fusion","Antimatter_Catalyzed_Fusion","Antimatter"]
def pclass_rank(c): return POWER_ORDER.index(c) if c in POWER_ORDER else 99
rows = []
for e in sorted(power, key=lambda x: (pclass_rank(x.get("powerPlantClass","?")), -float(x.get("maxOutput_GW",0) or 0))):
    rows.append([
        name_of(e),
        e.get("powerPlantClass","").replace("_"," "),
        fmt_cell(e.get("maxOutput_GW")),
        fmt_cell(e.get("specificPower_tGW")),
        fmt_cell(e.get("efficiency")),
        e.get("crew",0),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Power Plants.md", "Power Plants",
    "Provide GW of power for drives + lasers + particle weapons + utility. **Lower specific mass (t/GW) is better.** Some drive classes only run on matching plant types — check the Drives reference. Watch out: high-output plants need huge radiators to dump waste heat.",
    ["Name","Class","Output (GW)","t/GW","Eff.","Crew","Project"],
    rows)

# Habitat Modules
rows = []
for e in sorted(habs, key=lambda x: (x.get("tier", 99), x.get("baseMass_tons", 0))):
    incomes = []
    for k, v in e.items():
        if k.startswith("income") and v:
            res = k.replace("income","").replace("_month","")
            incomes.append(f"{res}+{v}")
    flags = []
    for k in ("coreModule","onePerHab","automated","allowsShipConstruction","allowsResupply","mine","alienModule"):
        if e.get(k): flags.append(k.replace('Module','').replace('allows','').replace('one','1'))
    rows.append([
        name_of(e),
        e.get("habType","Any"),
        e.get("tier",""),
        fmt_cell(e.get("baseMass_tons")),
        e.get("crew",0),
        e.get("power",0),
        e.get("buildTime_Days",0),
        e.get("controlPointCapacity",0),
        e.get("missionControl",0),
        ", ".join(incomes),
        ", ".join(flags),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Habitat Modules.md", "Habitat Modules",
    "Modules built on stations and bases. **Tier** unlocks via construction-tech projects; higher tier = better income, more power, more mass. Core modules (life support, comms, etc.) are mandatory. `1PerHab` modules are unique per habitat. Income columns show monthly resource generation.",
    ["Name","Type","Tier","Mass (t)","Crew","Power","Build (d)","CP cap","M.Ctrl","Income/mo","Flags","Project"],
    rows)

# Utility Modules
rows = []
for e in utility:
    sp = e.get("specialModuleRules") or []
    rows.append([
        name_of(e),
        fmt_cell(e.get("mass_tons")),
        e.get("crew",0),
        fmt_cell(e.get("powerRequirement_MW")),
        e.get("minConsTier",0),
        ", ".join(sp),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Utility Modules.md", "Utility Modules",
    "Ship utility slots: shipyard kits, mining modules, refit modules, sensors, ECM, etc. Some grant ship-build / mine / found-station capabilities; others give passive bonuses.",
    ["Name","Mass (t)","Crew","Power (MW)","Min tier","Special","Project"],
    rows)

# Ship Hulls
rows = []
for e in sorted(hulls, key=lambda x: (x.get("consTier", 99), x.get("mass_tons", 0))):
    rows.append([
        name_of(e),
        e.get("consTier",""),
        fmt_cell(e.get("length_m")),
        fmt_cell(e.get("mass_tons")),
        e.get("crew",0),
        e.get("maxOfficers",0),
        e.get("noseHardpoints",0),
        e.get("hullHardpoints",0),
        e.get("internalModules",0),
        e.get("missionControl",0),
        e.get("structuralIntegrity",""),
        e.get("baseConstructionTime_days",0),
        ("Yes" if e.get("alien") else ""),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Ship Hulls.md", "Ship Hulls",
    "Hull = chassis. Cons. tier gates which shipyards can build it. Hardpoints determine weapon capacity (nose = forward-fixed, hull = side turrets). Internal modules = utility/hab slots. Larger hulls → more crew, more mission control, more drive cap.",
    ["Name","Cons.","Length (m)","Mass (t)","Crew","Officers","Nose HP","Hull HP","Int. mods","M.Ctrl","SI","Build (d)","Alien?","Project"],
    rows)

# Armor
rows = []
for e in armor:
    sp = e.get("specialties") or []
    sp_str = ", ".join(f"{s.get('armorSpecialty','?')}={s.get('value',0)}" for s in sp if s.get('armorSpecialty') and s.get('armorSpecialty')!='None')
    rows.append([
        name_of(e),
        fmt_cell(e.get("density_kgm3")),
        fmt_cell(e.get("xRayHalfValue_cm")),
        fmt_cell(e.get("baryonicHalfValue_cm")),
        fmt_cell(e.get("heatofVaporization_MJkg")),
        sp_str,
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Armor.md", "Armor",
    "Surface armor for hulls. **Half-value (HV) cm** = the thickness needed to attenuate that radiation by half — _lower is better_. **Heat of vaporization (MJ/kg)** = energy to ablate one kg, _higher is better_. Specialties give multipliers vs specific damage types.",
    ["Name","Density (kg/m³)","X-ray HV (cm)","Baryon HV (cm)","Vap (MJ/kg)","Specialties","Project"],
    rows)

# Radiators
rows = []
for e in sorted(radiators, key=lambda x: -(float(x.get("specificPower_2s_KWkg",0) or 0))):
    rows.append([
        name_of(e),
        e.get("radiatorType",""),
        fmt_cell(e.get("operatingTemp_K")),
        fmt_cell(e.get("specificPower_2s_KWkg")),
        fmt_cell(e.get("specificMass_2s_kgm2")),
        fmt_cell(e.get("emissivity")),
        fmt_cell(e.get("vulnerability")),
        e.get("crew",0),
        ("Yes" if e.get("collector") else ""),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Radiators.md", "Radiators",
    "Dump waste heat from reactors / drives / weapons. **Higher specific power (kW/kg) is better.** Vulnerability is how easily damaged in combat (droplets > carbon panels). Hot radiators (high op-temp) are more efficient but harder to engineer.",
    ["Name","Type","Op temp (K)","kW/kg","kg/m²","Emissivity","Vulnerability","Crew","Collector","Project"],
    rows)

# Batteries
rows = []
for e in sorted(batteries, key=lambda x: -float(x.get("energyCapacity_GJ", 0) or 0)):
    rows.append([
        name_of(e),
        fmt_cell(e.get("energyCapacity_GJ")),
        fmt_cell(e.get("rechargeRate_GJs")),
        fmt_cell(e.get("mass_tons")),
        e.get("hp",""),
        e.get("crew",0),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Batteries.md", "Batteries",
    "Buffer reactor output for high-burst weapons (lasers, plasma). Capacity-to-mass ratio is the key figure of merit; recharge rate determines sustained fire after a salvo.",
    ["Name","Capacity (GJ)","Recharge (GJ/s)","Mass (t)","HP","Crew","Project"],
    rows)

# Heat Sinks
rows = []
for e in sorted(heatsinks, key=lambda x: -float(x.get("heatCapacity_GJ", 0) or 0)):
    rows.append([
        name_of(e),
        fmt_cell(e.get("heatCapacity_GJ")),
        fmt_cell(e.get("mass_tons")),
        e.get("crew",0),
        link_project(e.get("requiredProjectName")),
    ])
write_comparison("Heat Sinks.md", "Heat Sinks",
    "Absorb heat spikes when radiators can't keep up. Bigger capacity + lower mass = better. Used during stealth manoeuvres (no radiator emissions) and during burst combat.",
    ["Name","Capacity (GJ)","Mass (t)","Crew","Project"],
    rows)

# Top-level Ship Modules MOC
top = """---
name: Ship Modules
type: moc
tags:
  - moc
  - ship-modules
---

# Ship Modules — Reference

Comparison tables for every ship part in the game, sourced from the same JSON templates. Use these to decide whether researching a given project is worth it: each row links back to the unlocking project. Each project file also has a brief stat block injected showing what it grants.

## Weapons

- [[Magnetic Guns]] — coil cannons, mass drivers, railguns ({n_mg})
- [[Lasers]] — phasers, grasers, X-ray lasers ({n_l})
- [[Plasma Weapons]] — plasma cannons / lances ({n_p})
- [[Particle Weapons]] — neutral / charged particle beams ({n_pa})
- [[Conventional Guns]] — chemical cannons ({n_g})
- [[Missiles]] — kinetic, nuclear, antimatter torpedoes ({n_m})

## Propulsion & Power

- [[Drives]] — propulsion ({n_d} unique drive types, ~{n_d_var} variants total)
- [[Power Plants]] — reactors ({n_pp})
- [[Radiators]] — heat dissipation ({n_r})
- [[Batteries]] — energy buffers ({n_b})
- [[Heat Sinks]] — heat capacitors ({n_hs})

## Structure & Modules

- [[Ship Hulls]] — chassis ({n_h})
- [[Armor]] — surface armour ({n_a})
- [[Habitat Modules]] — station / base modules ({n_ham})
- [[Utility Modules]] — ship utility slots ({n_um})

## Reading the tables

- **Mass (t)** — module dry mass.
- **Crew** — required crew slots.
- **CD (s)** — main cooldown between salvos.
- **Salvo** — number of shots per cycle; **Intra (s)** is the gap between shots within a salvo.
- **Range (km)** — effective targeting range; weapons can fire further but accuracy collapses.
- **Bombardment** — strategic-layer ground-bombardment value.
- **Chip** — armor chipping per hit (helps strip enemy armor).
- **EV (km/s)** — drive exhaust velocity (≈ Isp × 9.8 m/s²); higher = more fuel-efficient.
- **t/GW** — power plant specific mass (lower is better).
- **HV (cm)** — armor half-value thickness (lower is better).
- **kW/kg** — radiator specific power (higher is better).
""".format(
    n_mg=len(magnetic_guns), n_l=len(lasers), n_p=len(plasma), n_pa=len(particle),
    n_g=len(guns), n_m=len(missiles),
    n_d=len(drive_by_proj), n_d_var=len(drives),
    n_pp=len(power), n_r=len(radiators), n_b=len(batteries), n_hs=len(heatsinks),
    n_h=len(hulls), n_a=len(armor), n_ham=len(habs), n_um=len(utility),
)
write(ROOT / "Ship Modules" / "_Ship Modules.md", top)

# Update _Home.md to add a Ship Modules link
home_path = ROOT / "_Home.md"
home_text = home_path.read_text(encoding="utf-8") if home_path.exists() else ""
if home_text and "[[_Ship Modules" not in home_text:
    insertion = "\n## Ship Modules\n\n- [[_Ship Modules|Ship Modules reference]] — comparison tables for every weapon, drive, hull, armor, etc.\n"
    # Insert before "## Source"
    home_text = home_text.replace("## Source", insertion + "\n## Source", 1)
    home_path.write_text(home_text, encoding="utf-8")
    print("Updated _Home.md with Ship Modules link.")

print("Done.")
