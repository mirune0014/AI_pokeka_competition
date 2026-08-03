import QtQuick
import "../src/ptcg_desktop/qml/components"

Row {
    width: 200
    height: 130
    spacing: 8

    CardTile {
        width: 82
        height: 114
        card: ({
            "card_id": 100,
            "state_token": "pokemon-1",
            "fallback_name": "Pokemon 1",
            "hp": 100,
            "max_hp": 120,
            "energies": [],
            "energy_cards": [],
            "tools": []
        })
        selectable: true
        choiceLabel: "1"
        selectedOrder: 0
    }

    CardTile {
        width: 82
        height: 114
        card: ({
            "card_id": 101,
            "state_token": "pokemon-2",
            "fallback_name": "Pokemon 2",
            "hp": 80,
            "max_hp": 120,
            "energies": [],
            "energy_cards": [],
            "tools": []
        })
        selectable: true
        choiceLabel: "2"
        selectedOrder: 1
    }
}
