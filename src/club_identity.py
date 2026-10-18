"""Explicit provider name equivalences; unknown clubs are never fuzzy matched."""

from dashboard_data import ALIASES, normalized_name

# Names used by the result archive, ESPN and Football-Data. Each row is one club.
GROUPS = [
    ["Bayern München", "Bayern Munich", "FC Bayern München"],
    ["Bor. Mönchengladbach", "Borussia Mönchengladbach", "M'gladbach"],
    ["1899 Hoffenheim", "TSG Hoffenheim", "TSG 1899 Hoffenheim", "Hoffenheim"],
    ["Eintracht Braunschweig", "TSV Eintracht Braunschweig", "Braunschweig"],
    ["Hertha BSC", "Hertha Berlin", "Hertha"],
    ["1. FC Kaiserslautern", "Kaiserslautern"],
    ["1. FC Nürnberg", "Nurnberg"],
    ["1. FC Köln", "FC Koln", "FC Cologne"],
    ["Bayer 04 Leverkusen", "Bayer Leverkusen", "Leverkusen"],
    ["Borussia Dortmund", "Dortmund"],
    ["Eintracht Frankfurt", "Ein Frankfurt"],
    ["SpVgg Greuther Fürth", "SpVgg Greuther Fürth 1903", "Greuther Furth"],
    ["VfL Bochum", "VfL Bochum 1848", "Bochum"],
    ["SV Darmstadt 98", "Darmstadt"],
    ["SC Freiburg", "Freiburg"],
    ["Hamburger SV", "Hamburg SV", "Hamburg"],
    ["Hannover 96", "Hannover"],
    ["FC Ingolstadt 04", "Ingolstadt"],
    ["SC Paderborn 07", "Paderborn"],
    ["VfB Stuttgart", "Stuttgart"],
    ["VfL Wolfsburg", "Wolfsburg"],
    ["FC Augsburg", "Augsburg"],
    ["1. FSV Mainz 05", "Mainz", "Mainz 05"],
    ["SV Werder Bremen", "Werder Bremen"],
    ["1. FC Union Berlin", "Union Berlin"],
    ["FC Schalke 04", "Schalke 04"],
    ["Fortuna Düsseldorf", "Fortuna Dusseldorf"],
    ["DSC Arminia Bielefeld", "Arminia Bielefeld", "Bielefeld"],
    ["1. FC Heidenheim 1846", "1. FC Heidenheim", "Heidenheim"],
    ["SV 07 Elversberg", "SV Elversberg", "Elversberg"],
    ["FC St. Pauli", "FC St. Pauli 1910", "St Pauli", "St. Pauli"],
    ["Birmingham", "Birmingham City"],
    ["Blackburn", "Blackburn Rovers"],
    ["Bolton", "Bolton Wanderers"],
    ["Brighton", "Brighton & Hove Albion"],
    ["Cardiff", "Cardiff City"],
    ["Coventry", "Coventry City"],
    ["Huddersfield", "Huddersfield Town"],
    ["Hull", "Hull City"],
    ["Ipswich", "Ipswich Town"],
    ["Leeds", "Leeds United"],
    ["Leicester", "Leicester City"],
    ["Luton", "Luton Town"],
    ["Man City", "Manchester City"],
    ["Man United", "Manchester United"],
    ["Newcastle", "Newcastle United"],
    ["Norwich", "Norwich City"],
    ["Nott'm Forest", "Nottingham Forest"],
    ["QPR", "Queens Park Rangers"],
    ["Stoke", "Stoke City"],
    ["Swansea", "Swansea City"],
    ["Tottenham", "Tottenham Hotspur"],
    ["West Brom", "West Bromwich Albion"],
    ["West Ham", "West Ham United"],
    ["Wigan", "Wigan Athletic"],
    ["Wolves", "Wolverhampton Wanderers"],
    ["Alavés", "CD Alavés", "Deportivo Alavés"],
    ["Almería", "UD Almería"],
    ["Ath Bilbao", "Athletic Club", "Athletic Bilbao"],
    ["Ath Madrid", "Atlético Madrid", "Club Atlético de Madrid"],
    ["Betis", "Real Betis", "Real Betis Balompié"],
    ["Celta", "Celta Vigo", "RC Celta", "RC Celta de Vigo"],
    ["Deportivo", "La Coruna", "Deportivo La Coruña", "RC Deportivo La Coruña"],
    ["Eibar", "SD Eibar"],
    ["Espanol", "Espanyol", "Espanyol Barcelona", "RCD Espanyol de Barcelona"],
    ["Huesca", "SD Huesca"],
    ["Las Palmas", "UD Las Palmas"],
    ["Leganés", "CD Leganés"],
    ["Mallorca", "RCD Mallorca"],
    ["Oviedo", "Real Oviedo"],
    ["Santander", "Racing Santander", "Real Racing Club de Santander"],
    ["Sociedad", "Real Sociedad", "Real Sociedad de Fútbol"],
    ["Sp Gijon", "Sporting Gijón"],
    ["Valladolid", "Real Valladolid"],
    ["Vallecano", "Rayo Vallecano", "Rayo Vallecano de Madrid"],
    ["Zaragoza", "Real Zaragoza"],
    ["Bologna", "Bologna FC 1909"],
    ["Chievo", "Chievo Verona"],
    ["Cremonese", "US Cremonese"],
    ["Inter", "Internazionale", "FC Internazionale Milano"],
    ["Lazio", "Lazio Roma", "SS Lazio"],
    ["Palermo", "US Palermo"],
    ["Parma", "Parma Calcio 1913"],
    ["Pescara", "Delfino Pescara"],
    ["Pisa", "AC Pisa 1909"],
    ["SPAL", "SPAL 2013 Ferrara"],
    ["Salernitana", "US Salernitana 1919"],
    ["Sampdoria", "UC Sampdoria"],
    ["Sassuolo", "US Sassuolo Calcio"],
    ["Verona", "Hellas Verona"],
    ["Ajaccio GFCO", "GFC Ajaccio", "Gazélec FC Ajaccio"],
    ["Amiens", "Amiens SC", "SC Amiens"],
    ["Auxerre", "AJ Auxerre"],
    ["Bastia", "SC Bastia"],
    ["Bordeaux", "Girondins Bordeaux"],
    ["Caen", "SM Caen"],
    ["Clermont", "Clermont Foot", "Clermont Foot 63"],
    ["Dijon", "Dijon FCO"],
    ["Guingamp", "EA Guingamp"],
    ["Lens", "RC Lens", "Racing Club de Lens"],
    ["Marseille", "Olympique Marseille", "Olympique de Marseille"],
    ["Montpellier", "Montpellier HSC"],
    ["Nancy", "AS Nancy Lorraine"],
    ["Nimes", "Nîmes Olympique"],
    ["Paris SG", "Paris Saint-Germain"],
    ["Reims", "Stade de Reims"],
    ["Rennes", "Stade Rennais", "Stade Rennais FC 1901"],
    ["St Etienne", "AS Saint-Étienne"],
    ["Strasbourg", "RC Strasbourg", "RC Strasbourg Alsace"],
    ["Troyes", "ESTAC Troyes", "ES Troyes AC"],
]


def equivalences():
    groups = [list(g) for g in GROUPS] + [[a, b] for a, b in ALIASES.items()]
    result = {}
    for names in groups:
        keys = {normalized_name(n) for n in names}
        existing = {result[k] for k in keys if k in result}
        canonical = min(keys | existing)
        for k, v in list(result.items()):
            if v in existing:
                result[k] = canonical
        result.update({k: canonical for k in keys})
    return result


EQUIVALENCES = equivalences()


def club_key(name):
    key = normalized_name(name)
    return EQUIVALENCES.get(key, key)


def resolver(names):
    lookup = {}
    for name in names:
        key = club_key(name)
        if key in lookup and lookup[key] != name:
            raise ValueError(f"Ambiguous club identity: {name}")
        lookup[key] = name
    return lambda name: lookup.get(club_key(name))
