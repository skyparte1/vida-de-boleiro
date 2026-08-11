from pathlib import Path

BASE_DIR = Path(__file__).parent
LOGOS_DIR = BASE_DIR / "static" / "club_logos"

# 211 associações-membro da FIFA.
# Os nomes das pastas usam os códigos FIFA de três letras.
FEDERATIONS = ['AFG', 'ALB', 'ALG', 'ASA', 'AND', 'ANG', 'AIA', 'ATG', 'ARG', 'ARM', 'ARU', 'AUS', 'AUT', 'AZE', 'BAH', 'BHR', 'BAN', 'BRB', 'BLR', 'BEL', 'BLZ', 'BEN', 'BER', 'BHU', 'BOL', 'BIH', 'BOT', 'BRA', 'VGB', 'BRU', 'BUL', 'BFA', 'BDI', 'CAM', 'CMR', 'CAN', 'CPV', 'CAY', 'CTA', 'CHA', 'CHI', 'CHN', 'TPE', 'COL', 'COM', 'CGO', 'COK', 'CRC', 'CRO', 'CUB', 'CUW', 'CYP', 'CZE', 'DEN', 'DJI', 'DMA', 'DOM', 'COD', 'ECU', 'EGY', 'SLV', 'ENG', 'EQG', 'ERI', 'EST', 'SWZ', 'ETH', 'FRO', 'FIJ', 'FIN', 'FRA', 'GAB', 'GAM', 'GEO', 'GER', 'GHA', 'GIB', 'GRE', 'GRN', 'GUM', 'GUA', 'GUI', 'GNB', 'GUY', 'HAI', 'HON', 'HKG', 'HUN', 'ISL', 'IND', 'IDN', 'IRN', 'IRQ', 'ISR', 'ITA', 'CIV', 'JAM', 'JPN', 'JOR', 'KAZ', 'KEN', 'KOS', 'KUW', 'KGZ', 'LAO', 'LVA', 'LBN', 'LES', 'LBR', 'LBY', 'LIE', 'LTU', 'LUX', 'MAC', 'MAD', 'MWI', 'MAS', 'MDV', 'MLI', 'MLT', 'MTN', 'MRI', 'MEX', 'MDA', 'MNG', 'MNE', 'MSR', 'MAR', 'MOZ', 'MYA', 'NAM', 'NEP', 'NED', 'NCL', 'NZL', 'NCA', 'NIG', 'NGA', 'PRK', 'MKD', 'NIR', 'NOR', 'OMA', 'PAK', 'PLE', 'PAN', 'PNG', 'PAR', 'PER', 'PHI', 'POL', 'POR', 'PUR', 'QAT', 'IRL', 'ROU', 'RUS', 'RWA', 'SKN', 'LCA', 'VIN', 'SAM', 'SMR', 'STP', 'KSA', 'SCO', 'SEN', 'SRB', 'SEY', 'SLE', 'SGP', 'SVK', 'SVN', 'SOL', 'SOM', 'RSA', 'KOR', 'SSD', 'ESP', 'SRI', 'SDN', 'SUR', 'SWE', 'SUI', 'SYR', 'TAH', 'TJK', 'TAN', 'THA', 'TLS', 'TOG', 'TGA', 'TRI', 'TUN', 'TUR', 'TKM', 'TCA', 'UGA', 'UKR', 'UAE', 'USA', 'URU', 'VIR', 'UZB', 'VAN', 'VEN', 'VIE', 'WAL', 'YEM', 'ZAM', 'ZIM']


def main():
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)

    created = 0
    already_exists = 0

    for code in FEDERATIONS:
        folder = LOGOS_DIR / code

        if folder.exists():
            already_exists += 1
        else:
            folder.mkdir(parents=True, exist_ok=True)
            created += 1

    existing_fifa_folders = {
        p.name
        for p in LOGOS_DIR.iterdir()
        if p.is_dir() and len(p.name) == 3
    }

    missing = sorted(set(FEDERATIONS) - existing_fifa_folders)

    print()
    print("Pastas das associações-membro da FIFA preparadas.")
    print(f"Criadas nesta execução: {created}")
    print(f"Já existentes: {already_exists}")
    print(f"Total esperado: {len(FEDERATIONS)}")
    print(f"Total encontrado: {len(set(FEDERATIONS) & existing_fifa_folders)}")

    if missing:
        print()
        print("ATENÇÃO: ainda faltam estas pastas:")
        for code in missing:
            print(f" - {code}")
    else:
        print()
        print("Validação concluída: as 211 pastas existem.")

    print()
    print(f"Local: {LOGOS_DIR}")


if __name__ == "__main__":
    main()
