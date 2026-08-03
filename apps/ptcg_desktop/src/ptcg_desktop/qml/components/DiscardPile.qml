import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Control {
    id: root
    objectName: "discardPile"
    property var cards: []
    property string heading: "トラッシュ"
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

    implicitWidth: 82
    implicitHeight: 116
    padding: 4

    background: Rectangle {
        radius: 8
        color: "#17352c"
        border.width: pileHover.hovered || discardPopup.opened ? 2 : 1
        border.color: pileHover.hovered || discardPopup.opened ? "#ffd45a" : "#6d8e82"
    }

    contentItem: Item {
        Rectangle {
            visible: root.cards && root.cards.length > 1
            anchors.centerIn: parent
            width: 58
            height: 82
            rotation: -5
            radius: 5
            color: "#d8d6ca"
            border.color: "#6d736f"
        }
        Rectangle {
            visible: root.cards && root.cards.length > 2
            anchors.centerIn: parent
            width: 58
            height: 82
            rotation: 5
            radius: 5
            color: "#ebe6d6"
            border.color: "#6d736f"
        }
        CardTile {
            anchors.centerIn: parent
            visible: root.cards && root.cards.length > 0
            card: root.cards && root.cards.length ? root.cards[root.cards.length - 1] : null
            compact: true
            interactive: false
            selectable: false
            onPreviewRequested: (card, active) => root.cardPreviewRequested(card, active)
        }
        Label {
            anchors.centerIn: parent
            visible: !root.cards || root.cards.length === 0
            text: "なし"
            color: "#b8cac3"
            font.pixelSize: 11
        }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 1
            width: countLabel.implicitWidth + 12
            height: countLabel.implicitHeight + 5
            radius: 8
            color: "#071f19"
            border.color: "#d2b953"
            Label {
                id: countLabel
                anchors.centerIn: parent
                text: root.heading + " " + (root.cards ? root.cards.length : 0)
                color: "white"
                font.pixelSize: 10
                font.bold: true
            }
        }
    }

    HoverHandler {
        id: pileHover
        onHoveredChanged: {
            if (hovered) {
                closeTimer.stop()
                discardPopup.open()
            } else {
                closeTimer.restart()
            }
        }
    }

    TapHandler {
        onTapped: discardPopup.opened ? discardPopup.close() : discardPopup.open()
    }

    Timer {
        id: closeTimer
        interval: 220
        repeat: false
        onTriggered: if (!popupHover.hovered && !pileHover.hovered) discardPopup.close()
    }

    Popup {
        id: discardPopup
        objectName: "discardPopup"
        parent: Overlay.overlay
        modal: false
        focus: false
        padding: 10
        width: Math.min(500, parent ? parent.width - 24 : 500)
        height: Math.min(390, 64 + Math.ceil(Math.max(1, root.cards ? root.cards.length : 0) / 5) * 112)
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        x: {
            if (!parent)
                return 0
            var point = root.mapToItem(parent, 0, 0)
            return Math.max(8, Math.min(parent.width - width - 8, point.x - width - 8))
        }
        y: {
            if (!parent)
                return 0
            var point = root.mapToItem(parent, 0, 0)
            return Math.max(8, Math.min(parent.height - height - 8, point.y))
        }

        background: Rectangle {
            radius: 12
            color: "#f4f1e7"
            border.width: 2
            border.color: "#315c4c"
        }

        contentItem: ColumnLayout {
            spacing: 6
            Label {
                Layout.fillWidth: true
                text: root.heading + "  " + (root.cards ? root.cards.length : 0) + "枚"
                color: "#17352c"
                font.pixelSize: 16
                font.bold: true
            }
            GridView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                cellWidth: 78
                cellHeight: 108
                model: root.cards || []
                ScrollBar.vertical: ScrollBar {}
                delegate: CardTile {
                    required property var modelData
                    width: 68
                    height: 96
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

        HoverHandler {
            id: popupHover
            onHoveredChanged: {
                if (hovered)
                    closeTimer.stop()
                else if (!pileHover.hovered)
                    closeTimer.restart()
            }
        }
    }
}
