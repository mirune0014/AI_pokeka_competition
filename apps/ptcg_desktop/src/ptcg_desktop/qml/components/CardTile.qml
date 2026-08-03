import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Control {
    id: root
    objectName: "cardTile"
    required property var card
    property bool compact: false
    property bool interactive: true
    property bool selectable: interactive
    property int selectedOrder: 0
    property string choiceLabel: ""
    signal activated(string targetToken)
    signal previewRequested(var card, bool active)

    readonly property int cardId: card && card.card_id !== undefined
                                  ? card.card_id
                                  : (card && card.id !== undefined ? card.id : 0)
    readonly property string targetToken: card && card.state_token ? card.state_token : ""
    readonly property string fallbackName: card && card.fallback_name
                                           ? card.fallback_name
                                           : (card && card.name ? card.name : "")

    function energyCount() {
        if (!root.card)
            return 0
        var typed = root.card.energies && root.card.energies.length ? root.card.energies.length : 0
        var cards = root.card.energy_cards && root.card.energy_cards.length ? root.card.energy_cards.length : 0
        return Math.max(typed, cards)
    }

    implicitWidth: compact ? 68 : 92
    implicitHeight: compact ? 96 : 128
    padding: 0
    focusPolicy: selectable ? Qt.StrongFocus : Qt.NoFocus

    background: Rectangle {
        radius: 7
        color: root.card ? "#f8f5e9" : "#25352f"
        border.width: root.selectedOrder > 0 ? 6 : (root.activeFocus ? 5 : (root.selectable ? 3 : 1))
        border.color: root.selectedOrder > 0 ? "#ffb000"
                                               : (root.activeFocus ? "#ffd45a"
                                                                   : (root.selectable ? "#35c6c1" : "#8aa197"))
    }

    contentItem: Item {
        Image {
            id: artwork
            anchors.fill: parent
            anchors.margins: 3
            source: root.cardId > 0 ? controller.cardImage(root.cardId, true) : ""
            fillMode: Image.PreserveAspectFit
            asynchronous: true
            cache: true
            sourceSize.width: 198
            sourceSize.height: 276
            visible: status === Image.Ready
        }

        Rectangle {
            anchors.fill: parent
            anchors.margins: 3
            radius: 5
            color: root.card ? "#e7dfc7" : "#1d2d28"
            visible: !artwork.visible

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 5
                spacing: 3
                Label {
                    Layout.fillWidth: true
                    text: root.card ? controller.cardName(root.cardId, root.fallbackName) : "裏向き"
                    color: root.card ? "#18201d" : "#b9c8c1"
                    font.pixelSize: root.compact ? 9 : 11
                    font.bold: true
                    wrapMode: Text.Wrap
                    horizontalAlignment: Text.AlignHCenter
                }
                Item { Layout.fillHeight: true }
            }
        }

        Rectangle {
            id: selectionTint
            objectName: "selectionTint"
            visible: root.selectedOrder > 0
            anchors.fill: parent
            anchors.margins: 3
            radius: 5
            color: "#55ffb000"
            border.width: 3
            border.color: "#fff2a8"
        }

        Rectangle {
            id: hpBadge
            objectName: "hpNumericBadge"
            visible: !!root.card && root.card.hp !== undefined
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 4
            width: hpLabel.implicitWidth + 8
            height: hpLabel.implicitHeight + 4
            radius: 7
            color: "#e8101815"
            border.width: 1
            border.color: "#f4f6ef"
            Label {
                id: hpLabel
                anchors.centerIn: parent
                text: root.card && root.card.hp !== undefined
                      ? "HP " + root.card.hp + "/" + root.card.max_hp
                      : ""
                color: "white"
                font.pixelSize: root.compact ? 8 : 10
                font.bold: true
            }
        }

        Rectangle {
            id: energyBadge
            objectName: "energyBadge"
            visible: root.energyCount() > 0
            anchors.left: parent.left
            anchors.bottom: hpBar.visible ? hpBar.top : parent.bottom
            anchors.leftMargin: 4
            anchors.bottomMargin: 3
            width: energyLabel.implicitWidth + 9
            height: energyLabel.implicitHeight + 4
            radius: 7
            color: "#e8c58919"
            border.width: 1
            border.color: "#fff0a6"
            Label {
                id: energyLabel
                anchors.centerIn: parent
                text: "⚡ " + root.energyCount()
                color: "#15130d"
                font.pixelSize: root.compact ? 9 : 11
                font.bold: true
            }
        }

        Rectangle {
            visible: !!root.card && !!root.card.tools && root.card.tools.length > 0
            anchors.right: parent.right
            anchors.bottom: hpBar.visible ? hpBar.top : parent.bottom
            anchors.rightMargin: 4
            anchors.bottomMargin: 3
            width: toolLabel.implicitWidth + 8
            height: toolLabel.implicitHeight + 4
            radius: 7
            color: "#e84a2868"
            Label {
                id: toolLabel
                anchors.centerIn: parent
                text: "道具 " + (root.card && root.card.tools ? root.card.tools.length : 0)
                color: "white"
                font.pixelSize: root.compact ? 8 : 9
                font.bold: true
            }
        }

        Rectangle {
            id: hpBar
            visible: !!root.card && root.card.hp !== undefined && root.card.max_hp > 0
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.margins: 4
            height: root.compact ? 5 : 7
            radius: 3
            color: "#26312d"
            border.width: 1
            border.color: "#eef3f0"

            Rectangle {
                height: parent.height - 2
                anchors.left: parent.left
                anchors.leftMargin: 1
                anchors.verticalCenter: parent.verticalCenter
                width: root.card && root.card.max_hp > 0
                       ? (parent.width - 2) * Math.max(0, Math.min(1, root.card.hp / root.card.max_hp))
                       : 0
                radius: 3
                color: root.card && root.card.max_hp > 0 && root.card.hp / root.card.max_hp > 0.5
                       ? "#45c66e"
                       : (root.card && root.card.max_hp > 0 && root.card.hp / root.card.max_hp > 0.2
                          ? "#efb940" : "#ed5d57")
                Behavior on width { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
            }
        }

        Rectangle {
            id: choiceNumberBadge
            objectName: "choiceNumberBadge"
            visible: root.choiceLabel.length > 0 || root.selectable
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.margins: 4
            radius: 5
            width: legalLabel.implicitWidth + 8
            height: legalLabel.implicitHeight + 4
            color: root.selectedOrder > 0 ? "#13723d" : "#073f43"
            border.width: root.selectedOrder > 0 ? 3 : 1
            border.color: "white"
            Label {
                id: legalLabel
                objectName: "choiceNumberText"
                anchors.centerIn: parent
                text: root.selectedOrder > 0
                      ? "✓ " + (root.choiceLabel.length > 0 ? root.choiceLabel : String(root.selectedOrder))
                      : (root.choiceLabel.length > 0 ? root.choiceLabel : "選択可")
                color: "white"
                font.pixelSize: root.compact ? 9 : 10
                font.bold: true
            }
        }

        Rectangle {
            visible: root.activeFocus
            anchors.right: parent.right
            anchors.top: hpBadge.visible ? hpBadge.bottom : parent.top
            anchors.margins: 4
            radius: 5
            width: focusLabel.implicitWidth + 8
            height: focusLabel.implicitHeight + 4
            color: "#2b2110"
            border.width: 2
            border.color: "white"
            Label {
                id: focusLabel
                anchors.centerIn: parent
                text: "焦点"
                color: "white"
                font.pixelSize: 8
                font.bold: true
            }
        }
    }

    HoverHandler {
        id: cardHover
        onHoveredChanged: root.previewRequested(root.card, hovered)
    }

    TapHandler {
        enabled: root.selectable && root.targetToken.length > 0
        onTapped: root.activated(root.targetToken)
    }

    onActiveFocusChanged: if (root.card) root.previewRequested(root.card, root.activeFocus)
    Keys.onSpacePressed: if (root.selectable && root.targetToken.length > 0) root.activated(root.targetToken)

    ToolTip.visible: cardHover.hovered && !!root.card
    ToolTip.text: root.card ? controller.cardName(root.cardId, root.fallbackName) : ""
    ToolTip.delay: 450

    Accessible.name: root.card ? controller.cardName(root.cardId, root.fallbackName) : "裏向きカード"
    Accessible.description: root.selectable
                            ? "合法対象 " + root.choiceLabel + "。Spaceで選択。選択後はカードの色が変わります。"
                            : "カーソルを合わせると右側に詳細を表示します。"
    Accessible.role: root.selectable ? Accessible.Button : Accessible.StaticText
}
