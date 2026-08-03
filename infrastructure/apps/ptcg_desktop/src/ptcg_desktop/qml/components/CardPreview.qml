import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Control {
    id: root
    objectName: "cardPreview"
    property var card: null
    property string placeholderText: "カードにカーソルを合わせると、ここに大きく表示されます。"

    readonly property int cardId: card && card.card_id !== undefined
                                  ? card.card_id
                                  : (card && card.id !== undefined ? card.id : 0)
    readonly property string fallbackName: card && card.fallback_name
                                           ? card.fallback_name
                                           : (card && card.name ? card.name : "")

    function cardNames(cards) {
        if (!cards || cards.length === 0)
            return "なし"
        var names = []
        for (var index = 0; index < cards.length; ++index) {
            var value = cards[index]
            if (!value)
                continue
            var id = value.card_id !== undefined ? value.card_id : (value.id !== undefined ? value.id : 0)
            var fallback = value.fallback_name ? value.fallback_name : (value.name ? value.name : "")
            names.push(controller.cardName(id, fallback))
        }
        return names.length ? names.join("、") : "なし"
    }

    function energyTypeName(value) {
        var names = {
            0: "無色", 1: "草", 2: "炎", 3: "水", 4: "雷", 5: "超", 6: "闘",
            7: "悪", 8: "鋼", 9: "ドラゴン", 10: "虹", 11: "ロケット団"
        }
        return names[value] || String(value)
    }

    function energyTypes(values) {
        if (!values || values.length === 0)
            return "なし"
        var names = []
        for (var index = 0; index < values.length; ++index)
            names.push(energyTypeName(values[index]))
        return names.join("、")
    }

    padding: 10
    background: Rectangle {
        radius: 12
        color: "#112a22"
        border.width: 1
        border.color: "#628477"
    }

    contentItem: ColumnLayout {
        spacing: 6

        Label {
            Layout.fillWidth: true
            text: root.card ? controller.cardName(root.cardId, root.fallbackName) : "カード詳細"
            color: "#fff4c5"
            font.pixelSize: 17
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            elide: Text.ElideRight
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 230

            Image {
                id: previewImage
                anchors.fill: parent
                anchors.margins: 2
                source: root.cardId > 0 ? controller.cardImage(root.cardId, false) : ""
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                cache: true
                sourceSize.width: 396
                sourceSize.height: 552
                visible: status === Image.Ready
            }

            Rectangle {
                anchors.fill: parent
                radius: 9
                color: "#1d3a31"
                border.color: "#456a5c"
                visible: !previewImage.visible
                Label {
                    anchors.centerIn: parent
                    width: parent.width - 32
                    text: root.card ? controller.cardName(root.cardId, root.fallbackName) : root.placeholderText
                    color: "#d5e3dd"
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: detailColumn.implicitHeight + 12
            radius: 8
            color: "#e9eee9"
            visible: !!root.card

            ColumnLayout {
                id: detailColumn
                anchors.fill: parent
                anchors.margins: 6
                spacing: 3

                Label {
                    Layout.fillWidth: true
                    visible: !!root.card && root.card.hp !== undefined
                    text: root.card && root.card.hp !== undefined
                          ? "現在HP  " + root.card.hp + " / " + root.card.max_hp
                            + "  （ダメージ " + Math.max(0, root.card.max_hp - root.card.hp) + "）"
                          : ""
                    color: "#19372d"
                    font.bold: true
                }
                Label {
                    Layout.fillWidth: true
                    visible: !!root.card && (root.card.energies !== undefined || root.card.energy_cards !== undefined)
                    text: root.card
                          ? "エネルギー: " + root.energyTypes(root.card.energies)
                            + (root.card.energy_cards && root.card.energy_cards.length
                               ? " / " + root.cardNames(root.card.energy_cards) : "")
                          : ""
                    color: "#30483f"
                    wrapMode: Text.Wrap
                }
                Label {
                    Layout.fillWidth: true
                    visible: !!root.card && !!root.card.tools && root.card.tools.length > 0
                    text: root.card && root.card.tools
                          ? "ポケモンのどうぐ: " + root.cardNames(root.card.tools)
                          : ""
                    color: "#30483f"
                    wrapMode: Text.Wrap
                }
                Label {
                    Layout.fillWidth: true
                    visible: previewImage.visible
                    text: "カード画像内の特性・ワザ・効果本文を確認できます。"
                    color: "#52665e"
                    font.pixelSize: 11
                    wrapMode: Text.Wrap
                }
            }
        }
    }
}
