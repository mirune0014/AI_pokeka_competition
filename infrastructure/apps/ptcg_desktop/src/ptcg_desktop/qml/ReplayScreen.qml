import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

FocusScope {
    id: root
    focus: true
    property var frame: controller.replayFrame || ({})
    property var payload: frame.payload || ({})
    property var current: payload.current || ({})
    property var players: current.players || []
    property int humanSeat: controller.resultData.human_seat === 1 ? 1 : 0
    property bool playing: false

    function turnPlayer() {
        if (current.turn === undefined || current.turn <= 0 || (current.first_player !== 0 && current.first_player !== 1))
            return -1
        return (current.first_player + current.turn - 1) % 2
    }

    function cardName(card) {
        if (!card)
            return "なし"
        return controller.cardName(card.id || 0, card.name || "")
    }

    Rectangle { anchors.fill: parent; color: "#172c25" }

    Keys.onLeftPressed: controller.replayPrevious()
    Keys.onRightPressed: controller.replayNext()
    Keys.onEscapePressed: controller.returnToResult()
    Keys.onSpacePressed: root.playing = !root.playing
    Shortcut { sequence: "Home"; onActivated: controller.replayFirst() }
    Shortcut { sequence: "End"; onActivated: controller.replayLast() }

    Timer {
        interval: 700
        repeat: true
        running: root.playing
        onTriggered: {
            if (controller.replayIndex + 1 < controller.replayCount)
                controller.replayNext()
            else
                root.playing = false
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 9

        RowLayout {
            Layout.fillWidth: true
            Button { text: "← 結果に戻る"; onClicked: controller.returnToResult() }
            Label { text: "ステップ式リプレイ"; color: "white"; font.pixelSize: 23; font.bold: true }
            Item { Layout.fillWidth: true }
            Switch {
                text: checked ? "全情報表示" : "人間視点"
                checked: controller.replayFullInformation
                onToggled: controller.setReplayFullInformation(checked)
                Accessible.name: "リプレイ表示情報の切り替え"
            }
        }

        Rectangle {
            visible: controller.replayFullInformation
            Layout.fillWidth: true
            implicitHeight: warningLabel.implicitHeight + 14
            radius: 8
            color: "#674f22"
            Label {
                id: warningLabel
                anchors.centerIn: parent
                width: parent.width - 20
                text: "終局後の全情報表示です。両者の手札・山札順・サイド内容を含みます。"
                color: "#fff2cf"
                font.bold: true
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
            }
        }

        Label {
            visible: !controller.replayFullInformation
            Layout.fillWidth: true
            text: "人間視点の保存済みスナップショットを表示しています。"
            color: "#c9d8d1"
            horizontalAlignment: Text.AlignHCenter
        }

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: replayCanvas.width
            contentHeight: replayCanvas.height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {}
            ScrollBar.horizontal: ScrollBar {}

            Item {
                id: replayCanvas
                width: Math.max(1040, root.width - 24)
                height: Math.max(760, replayLayout.implicitHeight + 20)

                RowLayout {
                    id: replayLayout
                    anchors.fill: parent
                    spacing: 12

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumWidth: 700
                        spacing: 9

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: replayHeader.implicitHeight + 20
                            radius: 10
                            color: "#0e3026"
                            RowLayout {
                                id: replayHeader
                                anchors.fill: parent
                                anchors.margins: 10
                                Label {
                                    text: "局面 " + (controller.replayIndex + 1) + " / " + controller.replayCount
                                          + "  ·  Turn " + (root.current.turn === undefined ? "-" : root.current.turn)
                                    color: "white"
                                    font.pixelSize: 18
                                    font.bold: true
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: "現在ターン: Player " + root.turnPlayer()
                                          + "  /  選択者: Player " + (root.current.acting_seat === undefined ? "-" : root.current.acting_seat)
                                          + "  /  先攻: Player " + (root.current.first_player === undefined ? "-" : root.current.first_player)
                                    color: "#d2dfd9"
                                    horizontalAlignment: Text.AlignRight
                                    wrapMode: Text.Wrap
                                }
                                Label {
                                    text: root.current.stadium && root.current.stadium.length
                                          ? "スタジアム: " + root.cardName(root.current.stadium[0])
                                          : "スタジアムなし"
                                    color: "#efd685"
                                }
                            }
                        }

                        PlayerField {
                            Layout.fillWidth: true
                            player: root.players.length > 1 ? root.players[1 - root.humanSeat] : ({})
                            heading: "AI（上）  Player " + (1 - root.humanSeat)
                            panelColor: "#244254"
                            showHandCards: controller.replayFullInformation
                            showSecrets: controller.replayFullInformation
                        }

                        PlayerField {
                            Layout.fillWidth: true
                            player: root.players.length > root.humanSeat ? root.players[root.humanSeat] : ({})
                            heading: "あなた（下）  Player " + root.humanSeat
                            panelColor: "#214a3c"
                            showHandCards: true
                            showSecrets: controller.replayFullInformation
                        }
                    }

                    GroupBox {
                        title: "公開ログから局面へ移動"
                        Layout.preferredWidth: 300
                        Layout.fillHeight: true

                        ListView {
                            anchors.fill: parent
                            clip: true
                            model: controller.replayPublicLog
                            spacing: 4

                            delegate: Button {
                                required property var modelData
                                width: ListView.view.width
                                text: "Step " + (modelData.revision === undefined ? "-" : modelData.revision)
                                      + "  " + (modelData.type || "")
                                      + (modelData.player_index !== undefined ? "  P" + modelData.player_index : "")
                                onClicked: controller.replaySeekRevision(modelData.revision || 0)
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Button { text: "⏮ 最初"; enabled: controller.replayIndex > 0; onClicked: controller.replayFirst() }
            Button { text: "◀ 一手戻る"; enabled: controller.replayIndex > 0; onClicked: controller.replayPrevious() }
            Button {
                text: root.playing ? "⏸ 停止" : "▶ 再生"
                enabled: controller.replayCount > 1
                onClicked: root.playing = !root.playing
            }
            Button { text: "一手進む ▶"; enabled: controller.replayIndex + 1 < controller.replayCount; onClicked: controller.replayNext() }
            Button { text: "最後 ⏭"; enabled: controller.replayIndex + 1 < controller.replayCount; onClicked: controller.replayLast() }
            Slider {
                from: 0
                to: Math.max(0, controller.replayCount - 1)
                stepSize: 1
                value: controller.replayIndex
                onMoved: controller.replaySeek(Math.round(value))
                Layout.preferredWidth: 220
                Accessible.name: "リプレイ局面"
            }
            SpinBox {
                from: controller.replayCount > 0 ? 1 : 0
                to: Math.max(1, controller.replayCount)
                value: controller.replayCount > 0 ? controller.replayIndex + 1 : 0
                editable: true
                onValueModified: if (controller.replayCount > 0) controller.replaySeek(value - 1)
                Accessible.name: "局面番号指定"
            }
        }
    }
}
