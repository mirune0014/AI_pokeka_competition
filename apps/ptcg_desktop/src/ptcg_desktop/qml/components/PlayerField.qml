import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Control {
    id: root
    required property var player
    property string heading: ""
    property color panelColor: "#1b4b3b"
    property bool showHandCards: false
    property bool showSecrets: false
    property var selectableForToken: function(token) { return false }
    property var selectedOrderForToken: function(token) { return 0 }
    property var choiceLabelForToken: function(token) { return "" }
    signal cardActivated(string targetToken)
    signal cardPreviewRequested(var card, bool active)

    function cardToken(card) {
        return card && card.state_token ? card.state_token : ""
    }

    function cardSelectable(card) {
        var token = cardToken(card)
        return token.length > 0 && !!selectableForToken && selectableForToken(token)
    }

    function cardOrder(card) {
        var token = cardToken(card)
        return token.length > 0 && !!selectedOrderForToken ? selectedOrderForToken(token) : 0
    }

    function cardChoiceLabel(card) {
        var token = cardToken(card)
        return token.length > 0 && !!choiceLabelForToken ? String(choiceLabelForToken(token)) : ""
    }

    function countOf(field, fallbackField) {
        if (player && player[field] !== undefined)
            return player[field]
        if (player && player[fallbackField] !== undefined && typeof player[fallbackField] === "number")
            return player[fallbackField]
        if (player && player[fallbackField] && player[fallbackField].length !== undefined)
            return player[fallbackField].length
        return 0
    }

    function conditionsText() {
        var c = player && player.conditions ? player.conditions : ({})
        var values = []
        if (c.poisoned) values.push("どく")
        if (c.burned) values.push("やけど")
        if (c.asleep) values.push("ねむり")
        if (c.paralyzed) values.push("マヒ")
        if (c.confused) values.push("こんらん")
        return values.length ? values.join("・") : "なし"
    }

    implicitHeight: fieldColumn.implicitHeight + 18
    padding: 9

    background: Rectangle {
        radius: 10
        color: root.panelColor
        border.color: "#78978c"
        border.width: 1
    }

    contentItem: ColumnLayout {
        id: fieldColumn
        spacing: 5

        RowLayout {
            Layout.fillWidth: true
            Label {
                text: root.heading
                color: "white"
                font.pixelSize: 16
                font.bold: true
            }
            Item { Layout.fillWidth: true }
            Label {
                text: "手札 " + root.countOf("hand_count", "handCount") + "枚"
                      + "  ·  山札 " + root.countOf("deck_count", "deckCount") + "枚"
                      + "  ·  サイド " + root.countOf("prize_count", "prize") + "枚"
                color: "#e8f0ec"
                font.pixelSize: 12
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 132
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 88
                Layout.fillHeight: true
                radius: 8
                color: "#16372d"
                border.color: "#557d6d"

                Column {
                    anchors.centerIn: parent
                    spacing: 8
                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "山札"
                        color: "#bcd2c9"
                        font.bold: true
                    }
                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: root.countOf("deck_count", "deckCount")
                        color: "white"
                        font.pixelSize: 24
                        font.bold: true
                    }
                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: "サイド " + root.countOf("prize_count", "prize")
                        color: "#ffe58f"
                        font.bold: true
                    }
                    Label {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 78
                        text: "状態: " + root.conditionsText()
                        color: "#cadbd4"
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                        horizontalAlignment: Text.AlignHCenter
                    }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 108
                Layout.fillHeight: true
                spacing: 2
                Label {
                    Layout.fillWidth: true
                    text: "バトル場"
                    color: "#d5e5de"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
                Row {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 4
                    Repeater {
                        model: root.player && root.player.active ? root.player.active : []
                        CardTile {
                            required property var modelData
                            width: 82
                            height: 114
                            card: modelData
                            selectable: root.cardSelectable(modelData)
                            selectedOrder: root.cardOrder(modelData)
                            choiceLabel: root.cardChoiceLabel(modelData)
                            onActivated: token => root.cardActivated(token)
                            onPreviewRequested: (card, active) => root.cardPreviewRequested(card, active)
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 2
                Label {
                    Layout.fillWidth: true
                    text: "ベンチ"
                    color: "#d5e5de"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
                Flickable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: benchRow.implicitWidth
                    clip: true
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.horizontal: ScrollBar {}

                    Row {
                        id: benchRow
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 6
                        Repeater {
                            model: root.player && root.player.bench ? root.player.bench : []
                            CardTile {
                                required property var modelData
                                card: modelData
                                compact: true
                                selectable: root.cardSelectable(modelData)
                                selectedOrder: root.cardOrder(modelData)
                                choiceLabel: root.cardChoiceLabel(modelData)
                                onActivated: token => root.cardActivated(token)
                                onPreviewRequested: (card, active) => root.cardPreviewRequested(card, active)
                            }
                        }
                        Repeater {
                            model: Math.max(0, (root.player && root.player.bench_max !== undefined
                                                ? root.player.bench_max : 5)
                                                - (root.player && root.player.bench ? root.player.bench.length : 0))
                            Rectangle {
                                width: 68
                                height: 96
                                radius: 7
                                color: "#17362d"
                                border.width: 1
                                border.color: "#456b5c"
                                Label {
                                    anchors.centerIn: parent
                                    text: "空き"
                                    color: "#77988b"
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }
                }
            }

            DiscardPile {
                Layout.preferredWidth: 82
                Layout.fillHeight: true
                cards: root.player && root.player.discard ? root.player.discard : []
                selectableForToken: function(token) { return root.selectableForToken(token) }
                selectedOrderForToken: function(token) { return root.selectedOrderForToken(token) }
                choiceLabelForToken: function(token) { return root.choiceLabelForToken(token) }
                onCardActivated: token => root.cardActivated(token)
                onCardPreviewRequested: (card, active) => root.cardPreviewRequested(card, active)
            }
        }

        RowLayout {
            visible: root.showHandCards
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 104 : 0
            spacing: 6

            Label {
                text: "手札"
                color: "#d7e4de"
                font.bold: true
                Layout.preferredWidth: 42
                horizontalAlignment: Text.AlignHCenter
            }
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: handRow.implicitWidth
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.horizontal: ScrollBar {}

                Row {
                    id: handRow
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6
                    Repeater {
                        model: root.showHandCards && root.player && root.player.hand ? root.player.hand : []
                        CardTile {
                            required property var modelData
                            card: modelData
                            compact: true
                            selectable: root.cardSelectable(modelData)
                            selectedOrder: root.cardOrder(modelData)
                            choiceLabel: root.cardChoiceLabel(modelData)
                            onActivated: token => root.cardActivated(token)
                            onPreviewRequested: (card, active) => root.cardPreviewRequested(card, active)
                        }
                    }
                }
            }
        }

        RowLayout {
            visible: root.showSecrets
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? 104 : 0
            spacing: 6
            Label {
                text: "サイド内容"
                color: "#d7e4de"
                font.bold: true
                Layout.preferredWidth: 76
                wrapMode: Text.Wrap
            }
            Flickable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                contentWidth: prizeRow.implicitWidth
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.horizontal: ScrollBar {}
                Row {
                    id: prizeRow
                    spacing: 5
                    Repeater {
                        model: root.showSecrets && root.player && root.player.prize ? root.player.prize : []
                        CardTile {
                            required property var modelData
                            card: modelData
                            compact: true
                            selectable: false
                            onPreviewRequested: (card, active) => root.cardPreviewRequested(card, active)
                        }
                    }
                }
            }
        }

        Label {
            visible: root.showSecrets
            Layout.fillWidth: true
            text: {
                if (!root.showSecrets || !root.player || !root.player.deck)
                    return ""
                var values = []
                for (var i = 0; i < root.player.deck.length; ++i) {
                    var card = root.player.deck[i]
                    var cardId = card && card.id !== undefined ? card.id : 0
                    values.push((i + 1) + ": " + controller.cardName(cardId, card && card.name ? card.name : ""))
                }
                return "山札順（先頭から）: " + values.join(" / ")
            }
            color: "#d7e4de"
            wrapMode: Text.Wrap
        }
    }
}
