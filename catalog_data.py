"""
Данные каталога продукции (загружено из Excel).
Не редактировать вручную! Используйте load_catalog_from_excel.py

Структура:
  CATALOG[category][product][line][type][diameter][gum_height][abutment_height] = {
    'name': 'Название товара',
    'sku': 'Артикул из 1C',
    'unit': 'Ед. изм.'
  }

  CATALOG[category][line]['no_size'] = [
    {'name': '...', 'sku': '...', 'unit': '...'},
    ...
  ]

VISIBILITY[category][level][item_name] = True/False
  level может быть: 'subcategory', 'line', 'product'
  True = показывать сразу, False = показывать в дополнительной кнопке
"""

CATALOG = {
    "Импланты": {
        "AOO": {
            3.5: {
                7.0: {"name": "AnyOne Onestage OSF3507H", "sku": "ANYONEONE-D35-L70", "unit": "шт", "qty": 3 },
                8.0: {"name": "AnyOne Onestage OSF3508H", "sku": "ANYONEONE-D35-L80", "unit": "шт", "qty": 7 },
                10.0: {"name": "AnyOne Onestage OSF3510H", "sku": "ANYONEONE-D35-L100", "unit": "шт", "qty": 6 },
                11.0: {"name": "AnyOne Onestage OSF3511H", "sku": "ANYONEONE-D35-L110", "unit": "шт", "qty": 10 },
            },
            4.0: {
                7.0: {"name": "AnyOne Onestage OSF4007H", "sku": "ANYONEONE-D40-L70", "unit": "шт", "qty": 5 },
                8.0: {"name": "AnyOne Onestage OSF4008H", "sku": "ANYONEONE-D40-L80", "unit": "шт", "qty": 5 },
                10.0: {"name": "AnyOne Onestage OSF4010H", "sku": "ANYONEONE-D40-L100", "unit": "шт", "qty": 5 },
                11.0: {"name": "AnyOne Onestage OSF4011H", "sku": "ANYONEONE-D40-L110", "unit": "шт", "qty": 5 },
            },
            4.5: {
                7.0: {"name": "AnyOne Onestage OSF4507H", "sku": "ANYONEONE-D45-L70", "unit": "шт", "qty": 5 },
                8.0: {"name": "AnyOne Onestage OSF4508LDH", "sku": "ANYONEONE-D45-L80", "unit": "шт", "qty": 5 },
            },
        },
        "ARi": {
            (3.5, 2.8): {
                5.0: {"name": "ARIE 283558M", "sku": "ARIE28355-D35-L50-H80", "unit": "шт", "qty": 8, "diameter_body": 2.8 },
                7.0: {"name": "ARIE 283576M", "sku": "ARIE28357-D35-L70-H60", "unit": "шт", "qty": 1, "diameter_body": 2.8 },
            },
            (4.0, 2.8): {
                5.0: {"name": "ARIE 284050M", "sku": "ARIE28405-D40-L50-H40", "unit": "шт", "qty": 3, "diameter_body": 2.8 },
                7.0: {"name": "ARIE 284076M", "sku": "ARIE28407-D40-L70-H60", "unit": "шт", "qty": 6, "diameter_body": 2.8 },
            },
            (4.0, 3.2): {
                5.0: {"name": "ARIE 324058M", "sku": "ARIE32405-D40-L50-H80", "unit": "шт", "qty": 5, "diameter_body": 3.2 },
                7.0: {"name": "ARIE 324078M", "sku": "ARIE32407-D40-L70-H80", "unit": "шт", "qty": 13, "diameter_body": 3.2 },
                9.0: {"name": "ARIE 324096M", "sku": "ARIE32409-D40-L90-H60", "unit": "шт", "qty": 4, "diameter_body": 3.2 },
            },
            (4.5, 3.2): {
                5.0: {"name": "ARIE 324558M", "sku": "ARIE32455-D45-L50-H80", "unit": "шт", "qty": 2, "diameter_body": 3.2 },
                7.0: {"name": "ARIE 324578M", "sku": "ARIE32457-D45-L70-H80", "unit": "шт", "qty": 10, "diameter_body": 3.2 },
                9.0: {"name": "ARIE 324596M", "sku": "ARIE32459-D45-L90-H60", "unit": "шт", "qty": 11, "diameter_body": 3.2 },
            },
        },
        "AnyOne": {
            3.5: {
                7.0: {"name": "AnyOne 3507 C", "sku": "AR-3507", "unit": "шт", "qty": 76 },
                8.0: {"name": "AnyOne 3508 C", "sku": "AR-3508", "unit": "шт", "qty": 24 },
                10.0: {"name": "AnyOne 3510 C", "sku": "AR-3510", "unit": "шт", "qty": 101 },
                13.0: {"name": "AnyOne 3513 C", "sku": "AO-3507C", "unit": "шт", "qty": 35 },
                15.0: {"name": "AnyOne 3515 C", "sku": "AO-3510C", "unit": "шт", "qty": 9 },
            },
            4.0: {
                7.0: {"name": "AnyOne 4007 C", "sku": "ANYONE400-D40-L70", "unit": "шт", "qty": 105 },
                8.0: {"name": "AnyOne 4008 C", "sku": "ANYONE400-D40-L80", "unit": "шт", "qty": 151 },
                10.0: {"name": "AnyOne 4010 C", "sku": "ANYONE401-D40-L100", "unit": "шт", "qty": 264 },
                11.0: {"name": "AnyOne 4011 C", "sku": "ANYONE401-D40-L110", "unit": "шт", "qty": 199 },
                13.0: {"name": "AnyOne 4013 C", "sku": "ANYONE401-D40-L130", "unit": "шт", "qty": 12 },
                15.0: {"name": "AnyOne 4015 C", "sku": "ANYONE401-D40-L150", "unit": "шт", "qty": 14 },
            },
            4.5: {
                7.0: {"name": "AnyOne 4507 C", "sku": "ANYONE450-D45-L70", "unit": "шт", "qty": 67 },
                8.0: {"name": "AnyOne 4508 C", "sku": "ANYONE450-D45-L80", "unit": "шт", "qty": 157 },
                10.0: {"name": "AnyOne 4510 C", "sku": "ANYONE451-D45-L100", "unit": "шт", "qty": 98 },
                11.0: {"name": "AnyOne 4511 C", "sku": "ANYONE451-D45-L110", "unit": "шт", "qty": 61 },
                13.0: {"name": "AnyOne 4513 C", "sku": "ANYONE451-D45-L130", "unit": "шт", "qty": 6 },
                15.0: {"name": "AnyOne 4515 C", "sku": "ANYONE451-D45-L150", "unit": "шт", "qty": 2 },
            },
            5.0: {
                7.0: {"name": "AnyOne 5007 C", "sku": "ANYONE500-D50-L70", "unit": "шт", "qty": 46 },
                8.0: {"name": "AnyOne 5008 C", "sku": "ANYONE500-D50-L80", "unit": "шт", "qty": 65 },
                10.0: {"name": "AnyOne 5010 C", "sku": "ANYONE501-D50-L100", "unit": "шт", "qty": 81 },
                11.0: {"name": "AnyOne 5011 C", "sku": "ANYONE501-D50-L110", "unit": "шт", "qty": 32 },
                13.0: {"name": "AnyOne 5013 C", "sku": "ANYONE501-D50-L130", "unit": "шт", "qty": 16 },
            },
            6.0: {
                7.0: {"name": "AnyOne 6007 C", "sku": "ANYONE600-D60-L70", "unit": "шт", "qty": 6 },
                10.0: {"name": "AnyOne 6010 C", "sku": "ANYONE601-D60-L100", "unit": "шт", "qty": 13 },
            },
            7.0: {
                7.0: {"name": "AnyOne 7007 C", "sku": "ANYONE700-D70-L70", "unit": "шт", "qty": 5 },
                8.0: {"name": "AnyOne 7008 C", "sku": "ANYONE700-D70-L80", "unit": "шт", "qty": 4 },
            },
        },
        "AnyOne DEEP": {
            4.5: {
                7.0: {"name": "AnyOne 4507 DC", "sku": "ANYONE450-D45-L70", "unit": "шт", "qty": 102 },
                8.0: {"name": "AnyOne 4508 DC", "sku": "ANYONE450-D45-L80", "unit": "шт", "qty": 126 },
                10.0: {"name": "AnyOne 4510 DC", "sku": "ANYONE451-D45-L100", "unit": "шт", "qty": 121 },
                11.0: {"name": "AnyOne 4511 DC", "sku": "ANYONE451-D45-L110", "unit": "шт", "qty": 111 },
                13.0: {"name": "AnyOne 4513 DC", "sku": "ANYONE451-D45-L130", "unit": "шт", "qty": 30 },
                15.0: {"name": "AnyOne 4515 DC", "sku": "ANYONE451-D45-L150", "unit": "шт", "qty": 5 },
            },
            5.5: {
                7.0: {"name": "AnyOne 5507 DC", "sku": "ANYONE550-D55-L70", "unit": "шт", "qty": 22 },
                8.0: {"name": "AnyOne 5508 DC", "sku": "ANYONE550-D55-L80", "unit": "шт", "qty": 1 },
                10.0: {"name": "AnyOne 5510 DC", "sku": "ANYONE551-D55-L100", "unit": "шт", "qty": 21 },
                11.0: {"name": "AnyOne 5511 DC", "sku": "ANYONE551-D55-L110", "unit": "шт", "qty": 12 },
                13.0: {"name": "AnyOne 5513 DC", "sku": "ANYONE551-D55-L130", "unit": "шт", "qty": 18 },
                15.0: {"name": "AnyOne 5515 DC", "sku": "ANYONE551-D55-L150", "unit": "шт", "qty": 5 },
            },
            6.5: {
                7.0: {"name": "AnyOne 6507 DC", "sku": "ANYONE650-D65-L70", "unit": "шт", "qty": 4 },
                8.0: {"name": "AnyOne 6508 DC", "sku": "ANYONE650-D65-L80", "unit": "шт", "qty": 16 },
                10.0: {"name": "AnyOne 6510 DC", "sku": "ANYONE651-D65-L100", "unit": "шт", "qty": 13 },
                11.0: {"name": "AnyOne 6511 DC", "sku": "ANYONE651-D65-L110", "unit": "шт", "qty": 15 },
            },
            7.5: {
                7.0: {"name": "AnyOne 7507DC", "sku": "ANYONE750-D75-L70", "unit": "шт", "qty": 2 },
                8.0: {"name": "AnyOne 7508DC", "sku": "ANYONE750-D75-L80", "unit": "шт", "qty": 7 },
            },
            8.0: {
                7.0: {"name": "AnyOne 8007 DC", "sku": "ANYONE800-D80-L70", "unit": "шт", "qty": 4 },
                8.0: {"name": "AnyOne 8008 DC", "sku": "ANYONE800-D80-L80", "unit": "шт", "qty": 8 },
            },
        },
        "AnyOne Special": {
            4.5: {
                7.0: {"name": "AnyOne 4507 SC", "sku": "ANYONE450-D45-L70", "unit": "шт", "qty": 5 },
            },
            5.0: {
                7.0: {"name": "AnyOne 5007 SC", "sku": "ANYONE500-D50-L70", "unit": "шт", "qty": 23 },
            },
            6.0: {
                8.0: {"name": "AnyOne 6007 SC", "sku": "ANYONE600-D60-L80", "unit": "шт", "qty": 2 },
            },
        },
        "AnyRidge": {
            3.5: {
                5.0: {"name": "AnyRidge MX 3505", "sku": "ANYRIDGEM-D35-L50", "unit": "шт", "qty": 26 },
                7.0: {"name": "AnyRidge 3507C", "sku": "ANYRIDGE3-D35-L70", "unit": "шт", "qty": 51 },
                8.0: {"name": "AnyRidge 3508 C", "sku": "ANYRIDGE3-D35-L80", "unit": "шт", "qty": 111 },
                10.0: {"name": "AnyRidge 3510 C", "sku": "ANYRIDGE3-D35-L100", "unit": "шт", "qty": 46 },
                11.0: {"name": "AnyRidge 3511 C", "sku": "ANYRIDGE3-D35-L110", "unit": "шт", "qty": 47 },
                13.0: {"name": "AnyRidge 3513 C", "sku": "ANYRIDGE3-D35-L130", "unit": "шт", "qty": 26 },
                15.0: {"name": "AnyRidge 3515 C", "sku": "ANYRIDGE3-D35-L150", "unit": "шт", "qty": 20 },
                18.0: {"name": "AnyRidge 3518 C", "sku": "ANYRIDGE3-D35-L180", "unit": "шт", "qty": 14 },
            },
            4.0: {
                5.0: {"name": "AnyRidge MX 4005", "sku": "ANYRIDGEM-D40-L50", "unit": "шт", "qty": 25 },
                7.0: {"name": "AnyRidge 4007 C", "sku": "ANYRIDGE4-D40-L70", "unit": "шт", "qty": 40 },
                8.0: {"name": "AnyRidge 4008 C", "sku": "ANYRIDGE4-D40-L80", "unit": "шт", "qty": 12 },
                10.0: {"name": "AnyRidge 4010 C", "sku": "ANYRIDGE4-D40-L100", "unit": "шт", "qty": 174 },
                11.0: {"name": "AnyRidge 4011 C", "sku": "ANYRIDGE4-D40-L110", "unit": "шт", "qty": 85 },
                13.0: {"name": "AnyRidge 4013 C", "sku": "ANYRIDGE4-D40-L130", "unit": "шт", "qty": 37 },
                15.0: {"name": "AnyRidge 4015 C", "sku": "ANYRIDGE4-D40-L150", "unit": "шт", "qty": 8 },
                18.0: {"name": "AnyRidge 4018 C", "sku": "ANYRIDGE4-D40-L180", "unit": "шт", "qty": 16 },
                25.0: {"name": "AnyRidge 4025 C", "sku": "ANYRIDGE4-D40-L250", "unit": "шт", "qty": 12 },
            },
            4.5: {
                5.0: {"name": "AnyRidge MX 4505", "sku": "ANYRIDGEM-D45-L50", "unit": "шт", "qty": 36 },
                7.0: {"name": "AnyRidge 4507 C", "sku": "ANYRIDGE4-D45-L70", "unit": "шт", "qty": 78 },
                8.0: {"name": "AnyRidge 4508 C", "sku": "ANYRIDGE4-D45-L80", "unit": "шт", "qty": 7 },
                11.0: {"name": "AnyRidge 4511 C", "sku": "ANYRIDGE4-D45-L110", "unit": "шт", "qty": 138 },
                13.0: {"name": "AnyRidge 4513 C", "sku": "ANYRIDGE4-D45-L130", "unit": "шт", "qty": 20 },
                15.0: {"name": "AnyRidge 4515 C", "sku": "ANYRIDGE4-D45-L150", "unit": "шт", "qty": 1 },
                18.0: {"name": "AnyRidge 4518 C", "sku": "ANYRIDGE4-D45-L180", "unit": "шт", "qty": 9 },
                25.0: {"name": "AnyRidge 4525 C", "sku": "ANYRIDGE4-D45-L250", "unit": "шт", "qty": 19 },
            },
            (4.5, 3.8): {
                7.0: {"name": "AnyRidge 384507 C", "sku": "ANYRIDGE3-D45-L70", "unit": "шт", "qty": 14, "diameter_body": 3.8 },
                11.0: {"name": "AnyRidge 384511 C", "sku": "ANYRIDGE3-D45-L110", "unit": "шт", "qty": 10, "diameter_body": 3.8 },
                13.0: {"name": "AnyRidge 384513 C", "sku": "ANYRIDGE3-D45-L130", "unit": "шт", "qty": 5, "diameter_body": 3.8 },
            },
            5.0: {
                5.0: {"name": "AnyRidge MX 5005", "sku": "ANYRIDGEM-D50-L50", "unit": "шт", "qty": 30 },
                7.0: {"name": "AnyRidge 5007 C", "sku": "ANYRIDGE5-D50-L70", "unit": "шт", "qty": 8 },
                8.0: {"name": "AnyRidge 5008 C", "sku": "ANYRIDGE5-D50-L80", "unit": "шт", "qty": 21 },
                10.0: {"name": "AnyRidge 5010 C", "sku": "ANYRIDGE5-D50-L100", "unit": "шт", "qty": 25 },
                11.0: {"name": "AnyRidge 5011 C", "sku": "ANYRIDGE5-D50-L110", "unit": "шт", "qty": 79 },
                13.0: {"name": "AnyRidge 5013 C", "sku": "ANYRIDGE5-D50-L130", "unit": "шт", "qty": 11 },
                15.0: {"name": "AnyRidge 5015 C", "sku": "ANYRIDGE5-D50-L150", "unit": "шт", "qty": 7 },
            },
            (5.0, 3.8): {
                7.0: {"name": "AnyRidge 385007 C", "sku": "ANYRIDGE3-D50-L70", "unit": "шт", "qty": 22, "diameter_body": 3.8 },
                10.0: {"name": "AnyRidge 385010 C", "sku": "ANYRIDGE3-D50-L100", "unit": "шт", "qty": 1, "diameter_body": 3.8 },
            },
            5.5: {
                7.0: {"name": "AnyRidge 5507 C", "sku": "ANYRIDGE5-D55-L70", "unit": "шт", "qty": 16 },
                8.0: {"name": "AnyRidge 5508 C", "sku": "ANYRIDGE5-D55-L80", "unit": "шт", "qty": 3 },
                10.0: {"name": "AnyRidge 5510 C", "sku": "ANYRIDGE5-D55-L100", "unit": "шт", "qty": 12 },
                11.0: {"name": "AnyRidge 5511 C", "sku": "ANYRIDGE5-D55-L110", "unit": "шт", "qty": 9 },
                13.0: {"name": "AnyRidge 5513 C", "sku": "ANYRIDGE5-D55-L130", "unit": "шт", "qty": 6 },
                15.0: {"name": "AnyRidge 5515 C", "sku": "ANYRIDGE5-D55-L150", "unit": "шт", "qty": 7 },
            },
            (5.5, 3.8): {
                7.0: {"name": "AnyRidge 385507 C", "sku": "ANYRIDGE3-D55-L70", "unit": "шт", "qty": 5, "diameter_body": 3.8 },
                8.0: {"name": "AnyRidge 385508 C", "sku": "ANYRIDGE3-D55-L80", "unit": "шт", "qty": 22, "diameter_body": 3.8 },
                10.0: {"name": "AnyRidge 385510 C", "sku": "ANYRIDGE3-D55-L100", "unit": "шт", "qty": 6, "diameter_body": 3.8 },
                15.0: {"name": "AnyRidge 385515 C", "sku": "ANYRIDGE3-D55-L150", "unit": "шт", "qty": 5, "diameter_body": 3.8 },
            },
            (5.5, 4.8): {
                13.0: {"name": "AnyRidge 485513 C", "sku": "ANYRIDGE4-D55-L130", "unit": "шт", "qty": 5, "diameter_body": 4.8 },
                15.0: {"name": "AnyRidge 485515 C", "sku": "ANYRIDGE4-D55-L150", "unit": "шт", "qty": 5, "diameter_body": 4.8 },
            },
            6.0: {
                8.0: {"name": "AnyRidge 6008 C", "sku": "ANYRIDGE6-D60-L80", "unit": "шт", "qty": 1 },
                10.0: {"name": "AnyRidge 6010 C", "sku": "ANYRIDGE6-D60-L100", "unit": "шт", "qty": 13 },
                13.0: {"name": "AnyRidge 6013 C", "sku": "ANYRIDGE6-D60-L130", "unit": "шт", "qty": 5 },
            },
            (6.0, 4.8): {
                7.0: {"name": "AnyRidge 486007 C", "sku": "ANYRIDGE4-D60-L70", "unit": "шт", "qty": 57, "diameter_body": 4.8 },
                8.0: {"name": "AnyRidge 486008 C", "sku": "ANYRIDGE4-D60-L80", "unit": "шт", "qty": 36, "diameter_body": 4.8 },
            },
            6.5: {
                7.0: {"name": "AnyRidge 6507 C", "sku": "ANYRIDGE6-D65-L70", "unit": "шт", "qty": 30 },
                8.0: {"name": "AnyRidge 6508 C", "sku": "ANYRIDGE6-D65-L80", "unit": "шт", "qty": 5 },
                10.0: {"name": "AnyRidge 6510 C", "sku": "ANYRIDGE6-D65-L100", "unit": "шт", "qty": 6 },
                11.0: {"name": "AnyRidge 6511 C", "sku": "ANYRIDGE6-D65-L110", "unit": "шт", "qty": 7 },
                13.0: {"name": "AnyRidge 6513 C", "sku": "ANYRIDGE6-D65-L130", "unit": "шт", "qty": 3 },
            },
            7.0: {
                7.0: {"name": "AnyRidge 7007C", "sku": "ANYRIDGE7-D70-L70", "unit": "шт", "qty": 25 },
                8.0: {"name": "AnyRidge 7008C", "sku": "ANYRIDGE7-D70-L80", "unit": "шт", "qty": 7 },
                10.0: {"name": "AnyRidge 7010C", "sku": "ANYRIDGE7-D70-L100", "unit": "шт", "qty": 2 },
                11.0: {"name": "AnyRidge 7011C", "sku": "ANYRIDGE7-D70-L110", "unit": "шт", "qty": 2 },
                13.0: {"name": "AnyRidge 7013C", "sku": "ANYRIDGE7-D70-L130", "unit": "шт", "qty": 4 },
            },
            7.5: {
                7.0: {"name": "AnyRidge 7507C", "sku": "ANYRIDGE7-D75-L70", "unit": "шт", "qty": 3 },
                8.0: {"name": "AnyRidge 7508C", "sku": "ANYRIDGE7-D75-L80", "unit": "шт", "qty": 7 },
                10.0: {"name": "AnyRidge 7510C", "sku": "ANYRIDGE7-D75-L100", "unit": "шт", "qty": 3 },
                11.0: {"name": "AnyRidge 7511C", "sku": "ANYRIDGE7-D75-L110", "unit": "шт", "qty": 4 },
                13.0: {"name": "AnyRidge 7513C", "sku": "ANYRIDGE7-D75-L130", "unit": "шт", "qty": 5 },
            },
            8.0: {
                7.0: {"name": "AnyRidge 8007C", "sku": "ANYRIDGE8-D80-L70", "unit": "шт", "qty": 7 },
                8.0: {"name": "AnyRidge 8008C", "sku": "ANYRIDGE8-D80-L80", "unit": "шт", "qty": 10 },
                10.0: {"name": "AnyRidge 8010C", "sku": "ANYRIDGE8-D80-L100", "unit": "шт", "qty": 8 },
                11.0: {"name": "AnyRidge 8011C", "sku": "ANYRIDGE8-D80-L110", "unit": "шт", "qty": 2 },
                13.0: {"name": "AnyRidge 8013C", "sku": "ANYRIDGE8-D80-L130", "unit": "шт", "qty": 5 },
            },
        },
        "BD Cuff": {
            3.7: {
                5.0: {"name": "BLUEDIMOND CUFF BDC370504C", "sku": "BLUEDIMOND-D37-L50-H40", "unit": "шт", "qty": 8 },
                7.0: {"name": "BLUEDIMOND CUFF BDC370702C", "sku": "BLUEDIMOND-D37-L70-H20", "unit": "шт", "qty": 3 },
            },
            4.1: {
                5.0: {"name": "BLUEDIMOND CUFF BDC410504C", "sku": "BLUEDIMOND-D41-L50-H40", "unit": "шт", "qty": 3 },
                7.0: {"name": "BLUEDIMOND CUFF BDC410702C", "sku": "BLUEDIMOND-D41-L70-H20", "unit": "шт", "qty": 5 },
            },
            4.4: {
                5.0: {"name": "BLUEDIMOND CUFF BDC440504C", "sku": "BLUEDIMOND-D44-L50-H40", "unit": "шт", "qty": 4 },
            },
        },
        "BD NC": {
            3.3: {
                7.0: {"name": "BLUEDIMOND NC ARO3307C", "sku": "BLUEDIMOND-D33-L70", "unit": "шт", "qty": 10 },
                8.0: {"name": "BLUEDIMOND NC ARO3308C", "sku": "BLUEDIMOND-D33-L80", "unit": "шт", "qty": 33 },
                10.0: {"name": "BLUEDIMOND NC ARO3310C", "sku": "BLUEDIMOND-D33-L100", "unit": "шт", "qty": 25 },
                11.0: {"name": "BLUEDIMOND NC ARO3311C", "sku": "BLUEDIMOND-D33-L110", "unit": "шт", "qty": 10 },
                13.0: {"name": "BLUEDIMOND NC ARO3313C", "sku": "BLUEDIMOND-D33-L130", "unit": "шт", "qty": 4 },
            },
            3.7: {
                7.0: {"name": "BLUEDIMOND NC ARO3707C", "sku": "BLUEDIMOND-D37-L70", "unit": "шт", "qty": 34 },
                8.0: {"name": "BLUEDIMOND NC ARO3708C", "sku": "BLUEDIMOND-D37-L80", "unit": "шт", "qty": 17 },
                10.0: {"name": "BLUEDIMOND NC ARO3710C", "sku": "BLUEDIMOND-D37-L100", "unit": "шт", "qty": 7 },
                11.0: {"name": "BLUEDIMOND NC ARO3711C", "sku": "BLUEDIMOND-D37-L110", "unit": "шт", "qty": 28 },
                13.0: {"name": "BLUEDIMOND NC ARO3713C", "sku": "BLUEDIMOND-D37-L130", "unit": "шт", "qty": 14 },
                15.0: {"name": "BLUEDIMOND NC ARO3715 DC", "sku": "BLUEDIMOND-D37-L150", "unit": "шт", "qty": 14 },
            },
        },
        "BD NC Deep": {
            3.3: {
                7.0: {"name": "BLUEDIMOND NC ARO3307 DC", "sku": "BLUEDIMOND-D33-L70", "unit": "шт", "qty": 26 },
                8.0: {"name": "BLUEDIMOND NC ARO3308 DC", "sku": "BLUEDIMOND-D33-L80", "unit": "шт", "qty": 7 },
                10.0: {"name": "BLUEDIMOND NC ARO3310 DC", "sku": "BLUEDIMOND-D33-L100", "unit": "шт", "qty": 8 },
                13.0: {"name": "BLUEDIMOND NC ARO3313 DC", "sku": "BLUEDIMOND-D33-L130", "unit": "шт", "qty": 13 },
            },
            3.7: {
                7.0: {"name": "BLUEDIMOND NC ARO3707 DC", "sku": "BLUEDIMOND-D37-L70", "unit": "шт", "qty": 26 },
                8.0: {"name": "BLUEDIMOND NC ARO3708 DC", "sku": "BLUEDIMOND-D37-L80", "unit": "шт", "qty": 27 },
                10.0: {"name": "BLUEDIMOND NC ARO3710 DC", "sku": "BLUEDIMOND-D37-L100", "unit": "шт", "qty": 17 },
                11.0: {"name": "BLUEDIMOND NC ARO3711 DC", "sku": "BLUEDIMOND-D37-L110", "unit": "шт", "qty": 13 },
                13.0: {"name": "BLUEDIMOND NC ARO3713 DC", "sku": "BLUEDIMOND-D37-L130", "unit": "шт", "qty": 10 },
            },
        },
        "BD RC": {
            4.1: {
                7.0: {"name": "BLUEDIMOND RC ARO4107C", "sku": "BLUEDIMOND-D41-L70", "unit": "шт", "qty": 27 },
                8.0: {"name": "BLUEDIMOND RC ARO4108C", "sku": "BLUEDIMOND-D41-L80", "unit": "шт", "qty": 9 },
                10.0: {"name": "BLUEDIMOND RC ARO4110C", "sku": "BLUEDIMOND-D41-L100", "unit": "шт", "qty": 15 },
                11.0: {"name": "BLUEDIMOND RC ARO4111C", "sku": "BLUEDIMOND-D41-L110", "unit": "шт", "qty": 10 },
                13.0: {"name": "BLUEDIMOND RC ARO4113C", "sku": "BLUEDIMOND-D41-L130", "unit": "шт", "qty": 10 },
            },
            4.4: {
                7.0: {"name": "BLUEDIMOND RC ARO4407C", "sku": "BLUEDIMOND-D44-L70", "unit": "шт", "qty": 1 },
                8.0: {"name": "BLUEDIMOND RC ARO4408C", "sku": "BLUEDIMOND-D44-L80", "unit": "шт", "qty": 16 },
                11.0: {"name": "BLUEDIMOND RC ARO4411C", "sku": "BLUEDIMOND-D44-L110", "unit": "шт", "qty": 12 },
                13.0: {"name": "BLUEDIMOND RC ARO4413C", "sku": "BLUEDIMOND-D44-L130", "unit": "шт", "qty": 5 },
                15.0: {"name": "BLUEDIMOND RC ARO4415C", "sku": "BLUEDIMOND-D44-L150", "unit": "шт", "qty": 4 },
            },
            4.8: {
                8.0: {"name": "BLUEDIMOND RC ARO4808C", "sku": "BLUEDIMOND-D48-L80", "unit": "шт", "qty": 4 },
                10.0: {"name": "BLUEDIMOND RC ARO4810C", "sku": "BLUEDIMOND-D48-L100", "unit": "шт", "qty": 9 },
                11.0: {"name": "BLUEDIMOND RC ARO4811C", "sku": "BLUEDIMOND-D48-L110", "unit": "шт", "qty": 2 },
            },
        },
        "BD RC Deep": {
            4.1: {
                7.0: {"name": "BLUEDIMOND RC ARO4107 DC", "sku": "BLUEDIMOND-D41-L70", "unit": "шт", "qty": 8 },
                8.0: {"name": "BLUEDIMOND RC ARO4108 DC", "sku": "BLUEDIMOND-D41-L80", "unit": "шт", "qty": 15 },
                10.0: {"name": "BLUEDIMOND RC ARO4110 DC", "sku": "BLUEDIMOND-D41-L100", "unit": "шт", "qty": 7 },
                11.0: {"name": "BLUEDIMOND RC ARO4111 DC", "sku": "BLUEDIMOND-D41-L110", "unit": "шт", "qty": 16 },
                13.0: {"name": "BLUEDIMOND RC ARO4113 DC", "sku": "BLUEDIMOND-D41-L130", "unit": "шт", "qty": 6 },
            },
            4.4: {
                7.0: {"name": "BLUEDIMOND RC ARO4407 DC", "sku": "BLUEDIMOND-D44-L70", "unit": "шт", "qty": 6 },
                8.0: {"name": "BLUEDIMOND RC ARO4408 DC", "sku": "BLUEDIMOND-D44-L80", "unit": "шт", "qty": 8 },
                10.0: {"name": "BLUEDIMOND RC ARO4410 DC", "sku": "BLUEDIMOND-D44-L100", "unit": "шт", "qty": 9 },
                11.0: {"name": "BLUEDIMOND RC ARO4411 DC", "sku": "BLUEDIMOND-D44-L110", "unit": "шт", "qty": 1 },
                13.0: {"name": "BLUEDIMOND RC ARO4413 DC", "sku": "BLUEDIMOND-D44-L130", "unit": "шт", "qty": 10 },
            },
            4.8: {
                7.0: {"name": "BLUEDIMOND RC ARO4807 DC", "sku": "BLUEDIMOND-D48-L70", "unit": "шт", "qty": 19 },
                8.0: {"name": "BLUEDIMOND RC ARO4808 DC", "sku": "BLUEDIMOND-D48-L80", "unit": "шт", "qty": 5 },
                10.0: {"name": "BLUEDIMOND RC ARO4810 DC", "sku": "BLUEDIMOND-D48-L100", "unit": "шт", "qty": 10 },
                11.0: {"name": "BLUEDIMOND RC ARO4811 DC", "sku": "BLUEDIMOND-D48-L110", "unit": "шт", "qty": 3 },
            },
            5.3: {
                7.0: {"name": "BLUEDIMOND RC ARO5307 DC", "sku": "BLUEDIMOND-D53-L70", "unit": "шт", "qty": 5 },
                8.0: {"name": "BLUEDIMOND RC ARO5308 DC", "sku": "BLUEDIMOND-D53-L80", "unit": "шт", "qty": 5 },
                10.0: {"name": "BLUEDIMOND RC ARO5310 DC", "sku": "BLUEDIMOND-D53-L100", "unit": "шт", "qty": 5 },
                11.0: {"name": "BLUEDIMOND RC ARO5311 DC", "sku": "BLUEDIMOND-D53-L110", "unit": "шт", "qty": 5 },
                13.0: {"name": "BLUEDIMOND RC ARO5313 DC", "sku": "BLUEDIMOND-D53-L130", "unit": "шт", "qty": 5 },
                15.0: {"name": "BLUEDIMOND RC ARO5315 DC", "sku": "BLUEDIMOND-D53-L150", "unit": "шт", "qty": 5 },
            },
            5.8: {
                8.0: {"name": "BLUEDIMOND RC ARO5808 DC", "sku": "BLUEDIMOND-D58-L80", "unit": "шт", "qty": 5 },
                10.0: {"name": "BLUEDIMOND RC ARO5810 DC", "sku": "BLUEDIMOND-D58-L100", "unit": "шт", "qty": 5 },
                11.0: {"name": "BLUEDIMOND RC ARO5811 DC", "sku": "BLUEDIMOND-D58-L110", "unit": "шт", "qty": 5 },
            },
            6.3: {
                8.0: {"name": "BLUEDIMOND RC ARO6308 DC", "sku": "BLUEDIMOND-D63-L80", "unit": "шт", "qty": 4 },
                10.0: {"name": "BLUEDIMOND RC ARO6310 DC", "sku": "BLUEDIMOND-D63-L100", "unit": "шт", "qty": 5 },
                11.0: {"name": "BLUEDIMOND RC ARO6311 DC", "sku": "BLUEDIMOND-D63-L110", "unit": "шт", "qty": 5 },
            },
        },
    },
    "Лаборатория": {
        "LabAn Цифр": {
            "AnyOne": {
                "no_size": [
                    {"name": "Analog (AO) AOIALRT (цифровой)", "sku": "LA-AR-45-15-27", "unit": "шт", "qty": 23 },
                ],
            },
            "Ari": {
                "no_size": [
                    {"name": "Analog NC (ARiE) ARIEALNT (sifrovoy)", "sku": "LA-AR-45-15-31", "unit": "шт", "qty": 23 },
                ],
            },
            "Mini": {
                "no_size": [
                    {"name": "Analog (MN) MNIALT цифровой", "sku": "LA-AR-45-15-28", "unit": "шт", "qty": 1 },
                ],
            },
            "ST": {
                "no_size": [
                    {"name": "Analog (ST) STIALRT (цифровой)", "sku": "LA-AR-45-15-30", "unit": "шт", "qty": 121 },
                ],
            },
            "STMini": {
                "no_size": [
                    {"name": "Analog (ST) STIALMT (цифровой)", "sku": "LA-AR-45-15-29", "unit": "шт", "qty": 30 },
                ],
            },
        },
        "LabAnalog": {
            "AO3,5": {
                    "Lab Analog (AO) LA 350H": {
                        "4.5": {
                            1.5: {
                            },
                        },
                    },
            },
            "AnyOne": {
                    "Lab Analog (AO) LA 400H": {
                        "4.5": {
                            1.5: {
                            },
                        },
                    },
            },
            "AnyRidge B": {
                    "Lab Analog (AR) AANLAF35": {
                        "3.5": {
                            8.0: {
                            },
                        },
                    },
            },
            "AnyRidge G": {
                    "Lab Analog (AR) AANLAF 4055": {
                        "4.0": {
                            55.0: {
                            },
                        },
                    },
            },
            "AnyRidge Y": {
                    "Lab Analog (AR) AALLAF 6080": {
                        "6.0": {
                            8.0: {
                            },
                        },
                    },
            },
            "Ari": {
                    "Lab Analog NC (ARiE) ARIEALA 2305": {
                        "2.3": {
                            5.0: {
                            },
                        },
                    },
                    "Lab Analog NC (ARiE) ARIEALA 2307": {
                        "2.3": {
                            7.0: {
                            },
                        },
                    },
                    "Lab Analog NC (ARiE) ARIEALA 2309": {
                        "2.3": {
                            9.0: {
                            },
                        },
                    },
            },
            "BD NC": {
                "no_size": [
                    {"name": "Lab Analog NC AROLAN", "sku": "LA-AR-45-15-33", "unit": "шт", "qty": 34 },
                    {"name": "Lab Analog NC BDIALNT", "sku": "LA-AO-45-15-33", "unit": "шт", "qty": 1 },
                ],
            },
            "BD RC": {
                "no_size": [
                    {"name": "Lab Analog RC AROLAR", "sku": "LA-EZ-408", "unit": "шт", "qty": 30 },
                    {"name": "Lab Analog RC BDIALRT", "sku": "LA-AR-45-15-26", "unit": "шт", "qty": 121 },
                ],
            },
            "Mini": {
                    "Lab Analog (MN) MILA300H": {
                        "3.0": {
                            8.0: {
                            },
                        },
                    },
            },
            "ST": {
                "no_size": [
                    {"name": "Lab Analog (ST) STTLA400", "sku": "LA-AO-45-15-31", "unit": "шт", "qty": 34 },
                ],
            },
            "STMini": {
                "no_size": [
                    {"name": "Lab Analog Mini (ST) STTLA350", "sku": "LA-EZ-406", "unit": "шт", "qty": 1 },
                ],
            },
        },
    },
    "Наборы": {
        "AUTOMAX": {
            "AUTOMAX": {
                "no_size": [
                    {"name": "Auto-Max Kit (CM) KAMS3000", "sku": "KAGAS2985", "unit": "компл", "qty": 1 },
                ],
            },
        },
        "AnchorKit": {
            "AnyOne": {
                "no_size": [
                    {"name": "Anchor Kit (AO) KAGAS3001", "sku": "KAGAS3001", "unit": "компл", "qty": 34 },
                ],
            },
            "AnyRidge": {
                "no_size": [
                    {"name": "Anchor Kit (AR) KAGAS3000", "sku": "KAGAS3000", "unit": "компл", "qty": 34 },
                ],
            },
        },
        "BonePro": {
            "AR/AO": {
                "no_size": [
                    {"name": "Bone Profiler Kit (AO/AR) KARBP3000", "sku": "KAGAS2986", "unit": "компл", "qty": 23 },
                ],
            },
        },
        "MICA": {
            "MICA": {
                "no_size": [
                    {"name": "MICA kit (CM) MKCA 3000S", "sku": "KAGAS2989", "unit": "компл", "qty": 1 },
                ],
            },
        },
        "MILA": {
            "MILA": {
                "no_size": [
                    {"name": "MILA Kit (CM) MKLA 3000M", "sku": "KAGAS2988", "unit": "компл", "qty": 30 },
                    {"name": "MILA Kit KLSCN 3000", "sku": "KAGAS2987", "unit": "компл", "qty": 121 },
                ],
            },
        },
        "R2G": {
            "ARi": {
                "no_size": [
                    {"name": "R2 ONE2 GUIDE Kit MKR20T3000S", "sku": "KAGAS2990", "unit": "компл", "qty": 34 },
                ],
            },
            "AnyOne": {
                "no_size": [
                    {"name": "R2 GUIDE Surgical Kit (AO) KAGIN3001", "sku": "KAGAS2994", "unit": "компл", "qty": 1 },
                ],
            },
            "AnyRidge": {
                "no_size": [
                    {"name": "R2 GUIDE Surgical Kit (AR) KAGIN3000", "sku": "KAGAS2993", "unit": "компл", "qty": 30 },
                ],
            },
            "BD NK": {
                "no_size": [
                    {"name": "R2 Narrow Kit (BD) KAGNS3000", "sku": "KAGAS2991", "unit": "компл", "qty": 23 },
                ],
            },
            "BlueDiamond": {
                "no_size": [
                    {"name": "R2 GUIDE Surgical Kit (BD) KAGIN3002", "sku": "KAGAS2992", "unit": "компл", "qty": 121 },
                ],
            },
        },
        "Хир.Набор": {
            "ARi": {
                "no_size": [
                    {"name": "Standart kit (ARi) MKARI 3000M", "sku": "KAGAS2998", "unit": "компл", "qty": 30 },
                ],
            },
            "AnyOne": {
                "no_size": [
                    {"name": "Standart Nabor (AO) KAOIN3003", "sku": "KAGAS2997", "unit": "компл", "qty": 121 },
                ],
            },
            "AnyRidge": {
                "no_size": [
                    {"name": "Surgical Kit Short (AR) KMXIS3000", "sku": "KAGAS2999", "unit": "компл", "qty": 1 },
                    {"name": "Standart Nabor (AR) KARIN3003", "sku": "KAGAS2996", "unit": "компл", "qty": 23 },
                    {"name": "Full Kit (AR) KARIN3001", "sku": "KAGAS2995", "unit": "компл", "qty": 34 },
                ],
            },
        },
    },
    "Протетика": {
        "EzPost": {
            "ARi": {
                    "Ez Post Abutment (ARiE) ARIEEPN 3507T [35Ncm]": {
                        "3.5": {
                            1.0: {
                                7.0: {"name": "Ez Post Abutment (ARiE) ARIEEPN 3507T [35Ncm]", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 1 },
                            },
                        },
                    },
            },
            "AnyOne": {
                    "Angled Abutment (AO) AA 4215 HT": {
                        "15": {
                            4.5: {
                                2.5: {
                                    7.0: {"name": "Angled Abutment (AO) AA 4215 HT", "sku": "ANGLEDABU-D45-L25-H70-15", "unit": "шт", "qty": 22 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AO) AA 4225 HT": {
                        "25": {
                            4.5: {
                                4.5: {
                                    7.0: {"name": "Angled Abutment (AO) AA 4225 HT", "sku": "ANGLEDABU-D45-L45-H70-25", "unit": "шт", "qty": 12 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AO) AA 4415 HT": {
                        "15": {
                            4.5: {
                                2.5: {
                                    7.0: {"name": "Angled Abutment (AO) AA 4415 HT", "sku": "ANGLEDABU-D45-L25-H70-15", "unit": "шт", "qty": 7 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AO) AA 4425 HT": {
                        "25": {
                            4.5: {
                                4.5: {
                                    7.0: {"name": "Angled Abutment (AO) AA 4425 HT", "sku": "ANGLEDABU-D45-L45-H70-25", "unit": "шт", "qty": 1 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AO) AA 5215 HT": {
                        "15": {
                            5.5: {
                                2.5: {
                                    7.0: {"name": "Angled Abutment (AO) AA 5215 HT", "sku": "ANGLEDABU-D55-L25-H70-15", "unit": "шт", "qty": 12 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AO) AA 5225 NT": {
                        "25": {
                            5.5: {
                                4.5: {
                                    7.0: {"name": "Angled Abutment (AO) AA 5225 NT", "sku": "ANGLEDABU-D55-L45-H70-25", "unit": "шт", "qty": 4 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AO) AA 5415 HT": {
                        "15": {
                            5.5: {
                                2.5: {
                                    7.0: {"name": "Angled Abutment (AO) AA 5415 HT", "sku": "ANGLEDABU-D55-L25-H70-15", "unit": "шт", "qty": 1 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AO) AA 5425 HT": {
                        "25": {
                            5.5: {
                                4.5: {
                                    7.0: {"name": "Angled Abutment (AO) AA 5425 HT", "sku": "ANGLEDABU-D55-L45-H70-25", "unit": "шт", "qty": 1 },
                                },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 4515 HT": {
                        "4.5": {
                            1.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 4515 HT", "sku": "EP-AR-45-15-25-ST", "unit": "шт", "qty": 49 },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 4525 HT": {
                        "4.5": {
                            2.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 4525 HT", "sku": "EP-AR-45-20-25-ST", "unit": "шт", "qty": 36 },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 4535 HT": {
                        "4.5": {
                            3.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 4535 HT", "sku": "EP-AR-45-15-25-AN", "unit": "шт", "qty": 23 },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 4545 HT": {
                        "4.5": {
                            4.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 4545 HT", "sku": "EP-AO-45-15-25-ST", "unit": "шт", "qty": 14 },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 5515 HT": {
                        "5.5": {
                            1.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 5515 HT", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 11 },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 5525 HT": {
                        "5.5": {
                            2.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 5525 HT", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 25 },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 5535 HT": {
                        "5.5": {
                            3.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 5535 HT", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 14 },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 5545 HT": {
                        "5.5": {
                            4.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 5545 HT", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 2 },
                            },
                        },
                    },
                    "EZ Post Abutment (AO) EP 6515 HT": {
                        "6.5": {
                            1.5: {
                                5.0: {"name": "EZ Post Abutment (AO) EP 6515 HT", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 4 },
                            },
                        },
                    },
            },
            "AnyRidge": {
                    "Angled Abutment (AR) AANAAE 4225L": {
                        "25": {
                            4.0: {
                                2.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAE 4225L", "sku": "ANGLEDABU-D40-L20-H70-25", "unit": "шт", "qty": 3 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAE 4325L": {
                        "25": {
                            4.0: {
                                3.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAE 4325L", "sku": "ANGLEDABU-D40-L30-H70-25", "unit": "шт", "qty": 3 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAE 5325L": {
                        "25": {
                            5.0: {
                                3.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAE 5325L", "sku": "ANGLEDABU-D50-L30-H70-25", "unit": "шт", "qty": 2 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 4215L": {
                        "15": {
                            4.0: {
                                2.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 4215L", "sku": "ANGLEDABU-D40-L20-H70-15", "unit": "шт", "qty": 4 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 4225L": {
                        "25": {
                            4.0: {
                                2.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 4225L", "sku": "ANGLEDABU-D40-L20-H70-25", "unit": "шт", "qty": 9 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 4315L": {
                        "15": {
                            4.0: {
                                3.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 4315L", "sku": "ANGLEDABU-D40-L30-H70-15", "unit": "шт", "qty": 5 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 4415L": {
                        "15": {
                            4.0: {
                                4.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 4415L", "sku": "ANGLEDABU-D40-L40-H70-15", "unit": "шт", "qty": 9 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 5215L": {
                        "15": {
                            5.0: {
                                2.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 5215L", "sku": "ANGLEDABU-D50-L20-H70-15", "unit": "шт", "qty": 12 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 5225L": {
                        "25": {
                            5.0: {
                                2.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 5225L", "sku": "ANGLEDABU-D50-L20-H70-25", "unit": "шт", "qty": 6 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 5315L": {
                        "15": {
                            5.0: {
                                3.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 5315L", "sku": "ANGLEDABU-D50-L30-H70-15", "unit": "шт", "qty": 2 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 5325L": {
                        "25": {
                            5.0: {
                                3.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 5325L", "sku": "ANGLEDABU-D50-L30-H70-25", "unit": "шт", "qty": 3 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 5415L": {
                        "15": {
                            5.0: {
                                4.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 5415L", "sku": "ANGLEDABU-D50-L40-H70-15", "unit": "шт", "qty": 2 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 5425L": {
                        "25": {
                            5.0: {
                                4.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 5425L", "sku": "ANGLEDABU-D50-L40-H70-25", "unit": "шт", "qty": 3 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (AR) AANAAH 6215L": {
                        "15": {
                            6.0: {
                                2.0: {
                                    7.0: {"name": "Angled Abutment (AR) AANAAH 6215L", "sku": "ANGLEDABU-D60-L20-H70-15", "unit": "шт", "qty": 20 },
                                },
                            },
                        },
                    },
                    "Ez Post Abutment (AR) AANEPH 4027L": {
                        "4.0": {
                            2.0: {
                                7.0: {"name": "Ez Post Abutment (AR) AANEPH 4027L", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 22 },
                            },
                        },
                    },
                    "Ez Post Abutment (AR) AANEPH 4037L": {
                        "4.0": {
                            3.0: {
                                7.0: {"name": "Ez Post Abutment (AR) AANEPH 4037L", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 10 },
                            },
                        },
                    },
                    "Ez Post Abutment (AR) AANEPH 4047L": {
                        "4.0": {
                            4.0: {
                                7.0: {"name": "Ez Post Abutment (AR) AANEPH 4047L", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 4 },
                            },
                        },
                    },
                    "Ez Post Abutment (AR) AANEPH 5027L": {
                        "5.0": {
                            2.0: {
                                7.0: {"name": "Ez Post Abutment (AR) AANEPH 5027L", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 12 },
                            },
                        },
                    },
                    "Ez Post Abutment (AR) AANEPH 5037L": {
                        "5.0": {
                            3.0: {
                                7.0: {"name": "Ez Post Abutment (AR) AANEPH 5037L", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 3 },
                            },
                        },
                    },
                    "Ez Post Abutment (AR) AANEPH 5047L": {
                        "5.0": {
                            4.0: {
                                7.0: {"name": "Ez Post Abutment (AR) AANEPH 5047L", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 1 },
                            },
                        },
                    },
                    "Ez Post Abutment (AR) AANEPH 6027L": {
                        "6.0": {
                            2.0: {
                                7.0: {"name": "Ez Post Abutment (AR) AANEPH 6027L", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 6 },
                            },
                        },
                    },
                    "Ez Post Abutment (AR) AANEPH 6035L": {
                        "6.0": {
                            3.0: {
                                5.0: {"name": "Ez Post Abutment (AR) AANEPH 6035L", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 4 },
                            },
                        },
                    },
            },
            "Mini": {
                    "Angled  Abutment (MINI) MIAA3215HT": {
                        "15": {
                            3.5: {
                                2.5: {
                                    7.0: {"name": "Angled  Abutment (MINI) MIAA3215HT", "sku": "ANGLEDAB-D35-L25-H70-15", "unit": "шт", "qty": 15 },
                                },
                            },
                        },
                    },
                    "Angled  Abutment (MINI) MIAA3315HT": {
                        "15": {
                            3.5: {
                                3.5: {
                                    7.0: {"name": "Angled  Abutment (MINI) MIAA3315HT", "sku": "ANGLEDAB-D35-L35-H70-15", "unit": "шт", "qty": 6 },
                                },
                            },
                        },
                    },
                    "Angled  Abutment (MINI) MIAA3415ET": {
                        "15": {
                            3.5: {
                                4.5: {
                                    7.0: {"name": "Angled  Abutment (MINI) MIAA3415ET", "sku": "ANGLEDAB-D35-L45-H70-15", "unit": "шт", "qty": 1 },
                                },
                            },
                        },
                    },
                    "Ez Post Abutment (MINI) MIEP3517HT": {
                        "3.5": {
                            1.5: {
                                7.0: {"name": "Ez Post Abutment (MINI) MIEP3517HT", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 5 },
                            },
                        },
                    },
                    "Ez Post Abutment (MINI) MIEP3527HT": {
                        "3.5": {
                            2.5: {
                                7.0: {"name": "Ez Post Abutment (MINI) MIEP3527HT", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 3 },
                            },
                        },
                    },
                    "Ez Post Abutment (MINI) MIEP3537HT": {
                        "3.5": {
                            3.5: {
                                7.0: {"name": "Ez Post Abutment (MINI) MIEP3537HT", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 8 },
                            },
                        },
                    },
            },
            "ST": {
                    "Angled Abutment (ST) STAA 4520 BT": {
                        "17": {
                            4.5: {
                                2.0: {
                                    8.0: {"name": "Angled Abutment (ST) STAA 4520 BT", "sku": "ANGLEDABU-D45-L20-H80-17", "unit": "шт", "qty": 122 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (ST) STAA 4540 BT": {
                        "17": {
                            4.5: {
                                4.0: {
                                    8.0: {"name": "Angled Abutment (ST) STAA 4540 BT", "sku": "ANGLEDABU-D45-L40-H80-17", "unit": "шт", "qty": 77 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (ST) STAA 5020 BT": {
                        "17": {
                            5.0: {
                                2.0: {
                                    8.0: {"name": "Angled Abutment (ST) STAA 5020 BT", "sku": "ANGLEDABU-D50-L20-H80-17", "unit": "шт", "qty": 11 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (ST) STAA 5040 BT": {
                        "17": {
                            5.0: {
                                4.0: {
                                    8.0: {"name": "Angled Abutment (ST) STAA 5040 BT", "sku": "ANGLEDABU-D50-L40-H80-17", "unit": "шт", "qty": 36 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (ST) STAA 6020 BT": {
                        "17": {
                            6.0: {
                                2.0: {
                                    8.0: {"name": "Angled Abutment (ST) STAA 6020 BT", "sku": "ANGLEDABU-D60-L20-H80-17", "unit": "шт", "qty": 16 },
                                },
                            },
                        },
                    },
                    "Angled Abutment (ST) STAA 6040 BT": {
                        "17": {
                            6.0: {
                                4.0: {
                                    8.0: {"name": "Angled Abutment (ST) STAA 6040 BT", "sku": "ANGLEDABU-D60-L40-H80-17", "unit": "шт", "qty": 10 },
                                },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 5710 T": {
                        "5.0": {
                            1.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 5710 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 106 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 5720 T": {
                        "5.0": {
                            2.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 5720 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 51 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 5730 T": {
                        "5.0": {
                            3.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 5730 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 29 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 5740 T": {
                        "5.0": {
                            4.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 5740 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 15 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 6710 T": {
                        "6.0": {
                            1.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 6710 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 17 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 6720 T": {
                        "6.0": {
                            2.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 6720 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 64 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 6730 T": {
                        "6.0": {
                            3.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 6730 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 22 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 6740 T": {
                        "6.0": {
                            4.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 6740 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 1 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEA 6750 T": {
                        "6.0": {
                            5.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEA 6750 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 1 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEAS 4711 T": {
                        "4.5": {
                            1.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEAS 4711 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 60 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEAS 4721 T": {
                        "4.5": {
                            2.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEAS 4721 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 31 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEAS 4731 T": {
                        "4.5": {
                            3.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEAS 4731 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 43 },
                            },
                        },
                    },
                    "Ezpost Abutment (ST) STEAS 4741 NT": {
                        },
                    "Ezpost Abutment (ST) STEAS 4741 T": {
                        "4.5": {
                            4.0: {
                                7.0: {"name": "Ezpost Abutment (ST) STEAS 4741 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 11 },
                            },
                        },
                    },
            },
            "STMini": {
                    "Angled Abutment MINI (ST) STAA 4520 MBT": {
                        "17": {
                            4.5: {
                                2.0: {
                                    8.0: {"name": "Angled Abutment MINI (ST) STAA 4520 MBT", "sku": "ANGLEDABU-D45-L20-H80-17", "unit": "шт", "qty": 22 },
                                },
                            },
                        },
                    },
                    "Angled Abutment MINI (ST) STAA 4540 MBT": {
                        "17": {
                            4.5: {
                                4.0: {
                                    8.0: {"name": "Angled Abutment MINI (ST) STAA 4540 MBT", "sku": "ANGLEDABU-D45-L40-H80-17", "unit": "шт", "qty": 30 },
                                },
                            },
                        },
                    },
                    "Ez Post Abutment MINI (ST) STEA 4711 T": {
                        "4.5": {
                            1.0: {
                                7.0: {"name": "Ez Post Abutment MINI (ST) STEA 4711 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 22 },
                            },
                        },
                    },
                    "Ez Post Abutment MINI (ST) STEA 4721 T": {
                        "4.5": {
                            2.0: {
                                7.0: {"name": "Ez Post Abutment MINI (ST) STEA 4721 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 58 },
                            },
                        },
                    },
                    "Ez Post Abutment MINI (ST) STEA 4731 T": {
                        "4.5": {
                            3.0: {
                                7.0: {"name": "Ez Post Abutment MINI (ST) STEA 4731 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 2 },
                            },
                        },
                    },
                    "Ez Post Abutment MINI (ST) STEA 4741 T": {
                        "4.5": {
                            4.0: {
                                7.0: {"name": "Ez Post Abutment MINI (ST) STEA 4741 T", "sku": "HA-AR-45-15-25-ST", "unit": "шт", "qty": 18 },
                            },
                        },
                    },
            },
        },
        "Формик": {
            "AnyOne": {
                    "Formiravatel (AO) HA 4030": {
                        "4.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4040": {
                        "4.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4050": {
                        "4.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4060": {
                        "4.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4070": {
                        "4.0": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4530": {
                        "4.5": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4540": {
                        "4.5": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4550": {
                        "4.5": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4560": {
                        "4.5": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 4570": {
                        "4.5": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 5530": {
                        "5.5": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 5540": {
                        "5.5": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 5550": {
                        "5.5": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 5560": {
                        "5.5": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 5570": {
                        "5.5": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 6530": {
                        "6.5": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 6540": {
                        "6.5": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 6550": {
                        "6.5": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 6560": {
                        "6.5": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 7540": {
                        "7.5": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 7550": {
                        "7.5": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 8540": {
                        "8.5": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 8550": {
                        "8.5": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 9540": {
                        "9.5": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AO) HA 9550": {
                        "9.5": {
                            5.0: {
                            },
                        },
                    },
            },
            "AnyRidge": {
                    "Formiravatel (AR) AANHAF0403": {
                        "4.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0404": {
                        "4.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0405": {
                        "4.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0406": {
                        "4.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0407": {
                        "4.0": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0504": {
                        "5.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0505": {
                        "5.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0506": {
                        "5.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0507": {
                        "5.0": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0603": {
                        "6.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0604": {
                        "6.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0605": {
                        "6.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0606": {
                        "6.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0607": {
                        "6.0": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0703": {
                        "7.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0704": {
                        "7.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0705": {
                        "7.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0706": {
                        "7.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0803": {
                        "8.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF0804": {
                        "8.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF1003": {
                        "10.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF1004": {
                        "10.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF1005": {
                        "10.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (AR) AANHAF1006": {
                        "10.0": {
                            6.0: {
                            },
                        },
                    },
            },
            "BD NC": {
                    "Formiravatel NC AROHAN402": {
                        "4.0": {
                            2.0: {
                            },
                        },
                    },
                    "Formiravatel NC AROHAN403": {
                        "4.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel NC AROHAN405": {
                        "4.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel NC AROHAN406": {
                        "4.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel NC AROHAN504": {
                        "5.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel NC AROHAN505": {
                        "5.0": {
                            5.0: {
                            },
                        },
                    },
            },
            "BD RC": {
                    "Formiravatel RC AROHAR404": {
                        "4.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel RC AROHAR405": {
                        "4.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel RC AROHAR406": {
                        "4.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel RC AROHAR504": {
                        "5.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel RC AROHAR505": {
                        "5.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel RC AROHAR506": {
                        "5.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel RC AROHAR604": {
                        "6.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel RC AROHAR605": {
                        "6.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel RC AROHAR606": {
                        "6.0": {
                            6.0: {
                            },
                        },
                    },
            },
            "Mini": {
                    "Formiravatel (MINI) MIHA3040": {
                        "3.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (MINI) MIHA3050": {
                        "3.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (MINI) MIHA3060": {
                        "3.0": {
                            6.0: {
                            },
                        },
                    },
                    "Formiravatel (MINI) MIHA3080": {
                        "3.0": {
                            8.0: {
                            },
                        },
                    },
                    "Formiravatel (MINI) MIHA3550": {
                        "3.5": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (MINI) MIHA3560": {
                        "3.5": {
                            6.0: {
                            },
                        },
                    },
            },
            "ST": {
                    "Formiravatel (ST) STHA403R": {
                        "4.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA404R": {
                        "4.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA405R": {
                        "4.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA407R": {
                        "4.0": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA453R": {
                        "4.5": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA454R": {
                        "4.5": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA455R": {
                        "4.5": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA457R": {
                        "4.5": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA503R": {
                        "5.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA504R": {
                        "5.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA505R": {
                        "5.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA507R": {
                        "5.0": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA604R": {
                        "6.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA605R": {
                        "6.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA607R": {
                        "6.0": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel (ST) STHA704R": {
                        "7.0": {
                            4.0: {
                            },
                        },
                    },
            },
            "STMini": {
                    "Formiravatel Mini (ST) STHA403M": {
                        "4.0": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel Mini (ST) STHA404M": {
                        "4.0": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel Mini (ST) STHA405M": {
                        "4.0": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel Mini (ST) STHA407M": {
                        "4.0": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel Mini (ST) STHA453M": {
                        "4.5": {
                            3.0: {
                            },
                        },
                    },
                    "Formiravatel Mini (ST) STHA454M": {
                        "4.5": {
                            4.0: {
                            },
                        },
                    },
                    "Formiravatel Mini (ST) STHA455M": {
                        "4.5": {
                            5.0: {
                            },
                        },
                    },
                    "Formiravatel Mini (ST) STHA457M": {
                        "4.5": {
                            7.0: {
                            },
                        },
                    },
                    "Formiravatel Mini (ST) STHA459M": {
                        "4.5": {
                            9.0: {
                            },
                        },
                    },
            },
        },
    },
    "материалы": {
        "Физик": {
            "Физик": {
                "no_size": [
                    {"name": "Fiziodisfensor COXO", "sku": "FZ-COXO", "unit": "шт", "qty": 2 },
                    {"name": "Fiziodisfensor Ki-20", "sku": "FZ-KI20", "unit": "шт", "qty": 2 },
                ],
            },
        },
    },
}

VISIBILITY = {
    "Импланты": {
        "line": {
            "AOO": False,
            "ARi": False,
            "AnyOne": True,
            "AnyOne DEEP": True,
            "AnyOne Special": True,
            "AnyRidge": True,
            "BD Cuff": False,
            "BD NC": False,
            "BD NC Deep": False,
            "BD RC": False,
            "BD RC Deep": False,
        },
    },
    "Лаборатория": {
        "line": {
            "AO3,5": True,
            "AnyOne": True,
            "AnyRidge B": True,
            "AnyRidge G": True,
            "AnyRidge Y": True,
            "Ari": True,
            "BD NC": True,
            "BD RC": True,
            "Mini": True,
            "ST": True,
            "STMini": True,
        },
        "product": {
            "Lab Analog (AO) LA 350H": True,
            "Lab Analog (AO) LA 400H": True,
            "Lab Analog (AR) AALLAF 6080": True,
            "Lab Analog (AR) AANLAF 4055": True,
            "Lab Analog (AR) AANLAF35": True,
            "Lab Analog (MN) MILA300H": True,
            "Lab Analog NC (ARiE) ARIEALA 2305": True,
            "Lab Analog NC (ARiE) ARIEALA 2307": True,
            "Lab Analog NC (ARiE) ARIEALA 2309": True,
        },
        "subcategory": {
            "LabAn Цифр": True,
            "LabAnalog": True,
        },
    },
    "Наборы": {
        "line": {
            "AR/AO": True,
            "ARi": True,
            "AUTOMAX": True,
            "AnyOne": True,
            "AnyRidge": True,
            "BD NK": True,
            "BlueDiamond": True,
            "MICA": True,
            "MILA": True,
        },
        "subcategory": {
            "AUTOMAX": True,
            "AnchorKit": True,
            "BonePro": True,
            "MICA": True,
            "MILA": True,
            "R2G": True,
            "Хир.Набор": True,
        },
    },
    "Протетика": {
        "line": {
            "ARi": True,
            "AnyOne": True,
            "AnyRidge": True,
            "BD NC": False,
            "BD RC": False,
            "Mini": True,
            "ST": True,
            "STMini": True,
        },
        "product": {
            "Angled  Abutment (MINI) MIAA3215HT": True,
            "Angled  Abutment (MINI) MIAA3315HT": True,
            "Angled  Abutment (MINI) MIAA3415ET": True,
            "Angled Abutment (AO) AA 4215 HT": True,
            "Angled Abutment (AO) AA 4225 HT": True,
            "Angled Abutment (AO) AA 4415 HT": True,
            "Angled Abutment (AO) AA 4425 HT": True,
            "Angled Abutment (AO) AA 5215 HT": True,
            "Angled Abutment (AO) AA 5225 NT": True,
            "Angled Abutment (AO) AA 5415 HT": True,
            "Angled Abutment (AO) AA 5425 HT": True,
            "Angled Abutment (AR) AANAAE 4225L": True,
            "Angled Abutment (AR) AANAAE 4325L": True,
            "Angled Abutment (AR) AANAAE 5325L": True,
            "Angled Abutment (AR) AANAAH 4215L": True,
            "Angled Abutment (AR) AANAAH 4225L": True,
            "Angled Abutment (AR) AANAAH 4315L": True,
            "Angled Abutment (AR) AANAAH 4415L": True,
            "Angled Abutment (AR) AANAAH 5215L": True,
            "Angled Abutment (AR) AANAAH 5225L": True,
            "Angled Abutment (AR) AANAAH 5315L": True,
            "Angled Abutment (AR) AANAAH 5325L": True,
            "Angled Abutment (AR) AANAAH 5415L": True,
            "Angled Abutment (AR) AANAAH 5425L": True,
            "Angled Abutment (AR) AANAAH 6215L": True,
            "Angled Abutment (ST) STAA 4520 BT": True,
            "Angled Abutment (ST) STAA 4540 BT": True,
            "Angled Abutment (ST) STAA 5020 BT": True,
            "Angled Abutment (ST) STAA 5040 BT": True,
            "Angled Abutment (ST) STAA 6020 BT": True,
            "Angled Abutment (ST) STAA 6040 BT": True,
            "Angled Abutment MINI (ST) STAA 4520 MBT": True,
            "Angled Abutment MINI (ST) STAA 4540 MBT": True,
            "EZ Post Abutment (AO) EP 4515 HT": True,
            "EZ Post Abutment (AO) EP 4525 HT": True,
            "EZ Post Abutment (AO) EP 4535 HT": True,
            "EZ Post Abutment (AO) EP 4545 HT": True,
            "EZ Post Abutment (AO) EP 5515 HT": True,
            "EZ Post Abutment (AO) EP 5525 HT": True,
            "EZ Post Abutment (AO) EP 5535 HT": True,
            "EZ Post Abutment (AO) EP 5545 HT": True,
            "EZ Post Abutment (AO) EP 6515 HT": True,
            "Ez Post Abutment (AR) AANEPH 4027L": True,
            "Ez Post Abutment (AR) AANEPH 4037L": True,
            "Ez Post Abutment (AR) AANEPH 4047L": True,
            "Ez Post Abutment (AR) AANEPH 5027L": True,
            "Ez Post Abutment (AR) AANEPH 5037L": True,
            "Ez Post Abutment (AR) AANEPH 5047L": True,
            "Ez Post Abutment (AR) AANEPH 6027L": True,
            "Ez Post Abutment (AR) AANEPH 6035L": True,
            "Ez Post Abutment (ARiE) ARIEEPN 3507T [35Ncm]": True,
            "Ez Post Abutment (MINI) MIEP3517HT": True,
            "Ez Post Abutment (MINI) MIEP3527HT": True,
            "Ez Post Abutment (MINI) MIEP3537HT": True,
            "Ez Post Abutment MINI (ST) STEA 4711 T": True,
            "Ez Post Abutment MINI (ST) STEA 4721 T": True,
            "Ez Post Abutment MINI (ST) STEA 4731 T": True,
            "Ez Post Abutment MINI (ST) STEA 4741 T": True,
            "Ezpost Abutment (ST) STEA 5710 T": True,
            "Ezpost Abutment (ST) STEA 5720 T": True,
            "Ezpost Abutment (ST) STEA 5730 T": True,
            "Ezpost Abutment (ST) STEA 5740 T": True,
            "Ezpost Abutment (ST) STEA 6710 T": True,
            "Ezpost Abutment (ST) STEA 6720 T": True,
            "Ezpost Abutment (ST) STEA 6730 T": True,
            "Ezpost Abutment (ST) STEA 6740 T": True,
            "Ezpost Abutment (ST) STEA 6750 T": True,
            "Ezpost Abutment (ST) STEAS 4711 T": True,
            "Ezpost Abutment (ST) STEAS 4721 T": True,
            "Ezpost Abutment (ST) STEAS 4731 T": True,
            "Ezpost Abutment (ST) STEAS 4741 NT": True,
            "Ezpost Abutment (ST) STEAS 4741 T": True,
            "Formiravatel (AO) HA 4030": False,
            "Formiravatel (AO) HA 4040": False,
            "Formiravatel (AO) HA 4050": False,
            "Formiravatel (AO) HA 4060": False,
            "Formiravatel (AO) HA 4070": False,
            "Formiravatel (AO) HA 4530": False,
            "Formiravatel (AO) HA 4540": False,
            "Formiravatel (AO) HA 4550": False,
            "Formiravatel (AO) HA 4560": False,
            "Formiravatel (AO) HA 4570": False,
            "Formiravatel (AO) HA 5530": False,
            "Formiravatel (AO) HA 5540": False,
            "Formiravatel (AO) HA 5550": False,
            "Formiravatel (AO) HA 5560": False,
            "Formiravatel (AO) HA 5570": False,
            "Formiravatel (AO) HA 6530": False,
            "Formiravatel (AO) HA 6540": False,
            "Formiravatel (AO) HA 6550": False,
            "Formiravatel (AO) HA 6560": False,
            "Formiravatel (AO) HA 7540": False,
            "Formiravatel (AO) HA 7550": False,
            "Formiravatel (AO) HA 8540": False,
            "Formiravatel (AO) HA 8550": False,
            "Formiravatel (AO) HA 9540": False,
            "Formiravatel (AO) HA 9550": False,
            "Formiravatel (AR) AANHAF0403": False,
            "Formiravatel (AR) AANHAF0404": False,
            "Formiravatel (AR) AANHAF0405": False,
            "Formiravatel (AR) AANHAF0406": False,
            "Formiravatel (AR) AANHAF0407": False,
            "Formiravatel (AR) AANHAF0504": False,
            "Formiravatel (AR) AANHAF0505": False,
            "Formiravatel (AR) AANHAF0506": False,
            "Formiravatel (AR) AANHAF0507": False,
            "Formiravatel (AR) AANHAF0603": False,
            "Formiravatel (AR) AANHAF0604": False,
            "Formiravatel (AR) AANHAF0605": False,
            "Formiravatel (AR) AANHAF0606": False,
            "Formiravatel (AR) AANHAF0607": False,
            "Formiravatel (AR) AANHAF0703": False,
            "Formiravatel (AR) AANHAF0704": False,
            "Formiravatel (AR) AANHAF0705": False,
            "Formiravatel (AR) AANHAF0706": False,
            "Formiravatel (AR) AANHAF0803": False,
            "Formiravatel (AR) AANHAF0804": False,
            "Formiravatel (AR) AANHAF1003": False,
            "Formiravatel (AR) AANHAF1004": False,
            "Formiravatel (AR) AANHAF1005": False,
            "Formiravatel (AR) AANHAF1006": False,
            "Formiravatel (MINI) MIHA3040": False,
            "Formiravatel (MINI) MIHA3050": False,
            "Formiravatel (MINI) MIHA3060": False,
            "Formiravatel (MINI) MIHA3080": False,
            "Formiravatel (MINI) MIHA3550": False,
            "Formiravatel (MINI) MIHA3560": False,
            "Formiravatel (ST) STHA403R": False,
            "Formiravatel (ST) STHA404R": False,
            "Formiravatel (ST) STHA405R": False,
            "Formiravatel (ST) STHA407R": False,
            "Formiravatel (ST) STHA453R": False,
            "Formiravatel (ST) STHA454R": False,
            "Formiravatel (ST) STHA455R": False,
            "Formiravatel (ST) STHA457R": False,
            "Formiravatel (ST) STHA503R": False,
            "Formiravatel (ST) STHA504R": False,
            "Formiravatel (ST) STHA505R": False,
            "Formiravatel (ST) STHA507R": False,
            "Formiravatel (ST) STHA604R": False,
            "Formiravatel (ST) STHA605R": False,
            "Formiravatel (ST) STHA607R": False,
            "Formiravatel (ST) STHA704R": False,
            "Formiravatel Mini (ST) STHA403M": False,
            "Formiravatel Mini (ST) STHA404M": False,
            "Formiravatel Mini (ST) STHA405M": False,
            "Formiravatel Mini (ST) STHA407M": False,
            "Formiravatel Mini (ST) STHA453M": False,
            "Formiravatel Mini (ST) STHA454M": False,
            "Formiravatel Mini (ST) STHA455M": False,
            "Formiravatel Mini (ST) STHA457M": False,
            "Formiravatel Mini (ST) STHA459M": False,
            "Formiravatel NC AROHAN402": False,
            "Formiravatel NC AROHAN403": False,
            "Formiravatel NC AROHAN405": False,
            "Formiravatel NC AROHAN406": False,
            "Formiravatel NC AROHAN504": False,
            "Formiravatel NC AROHAN505": False,
            "Formiravatel RC AROHAR404": False,
            "Formiravatel RC AROHAR405": False,
            "Formiravatel RC AROHAR406": False,
            "Formiravatel RC AROHAR504": False,
            "Formiravatel RC AROHAR505": False,
            "Formiravatel RC AROHAR506": False,
            "Formiravatel RC AROHAR604": False,
            "Formiravatel RC AROHAR605": False,
            "Formiravatel RC AROHAR606": False,
        },
        "subcategory": {
            "EzPost": True,
            "Формик": False,
        },
    },
    "материалы": {
        "line": {
            "Физик": True,
        },
        "subcategory": {
            "Физик": True,
        },
    },
}
