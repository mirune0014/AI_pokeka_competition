import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

FocusScope {
    id: root
    property var result: controller.resultData || ({})
    property var diagnostics: controller.diagnosticsData || ({})

    function outcomeTitle() {
        if (result.classification === "system_error")
            return "対戦を完了できませんでした"
        if (result.classification === "technical_forfeit")
            return "AIの技術的敗北 / あなたの勝利"
        if (result.winner_seat === null || result.winner_seat === undefined)
            return "引き分け"
        return result.winner_seat === result.human_seat ? "あなたの勝利" : "あなたの敗北"
    }

    function categoryText() {
        if (result.classification === "normal")
            return "通常勝敗"
        if (result.classification === "technical_forfeit")
            return "技術的敗北"
        if (result.classification === "system_error")
            return "システム異常"
        return result.classification || "-"
    }

    function seatRole() {
        if (result.human_seat !== 0 && result.human_seat !== 1)
            return "-"
        if (result.first_player !== 0 && result.first_player !== 1)
            return "Player " + result.human_seat + " / 先攻・後攻未確定"
        return "Player " + result.human_seat + " / " + (result.human_seat === result.first_player ? "先攻" : "後攻")
    }

    Rectangle { anchors.fill: parent; color: "#f1efe8" }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: Math.min(820, Math.max(560, root.width - 48))
            x: Math.max(20, (Math.max(600, root.width) - width) / 2)
            spacing: 18

            Item { Layout.preferredHeight: 18 }

            Label {
                Layout.fillWidth: true
                text: root.outcomeTitle()
                color: root.result.classification === "system_error" ? "#8b332f" : "#173c31"
                font.pixelSize: 34
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: details.implicitHeight + 36
                radius: 12
                color: "white"
                border.color: "#b3b8b4"

                GridLayout {
                    id: details
                    anchors.fill: parent
                    anchors.margins: 18
                    columns: 2
                    columnSpacing: 18
                    rowSpacing: 8

                    Label { text: "結果"; font.bold: true; color: "#52605a" }
                    Label { Layout.fillWidth: true; text: root.result.summary_ja || ""; wrapMode: Text.Wrap; color: "#26352f"; font.pixelSize: 17 }
                    Label { text: "分類"; font.bold: true; color: "#52605a" }
                    Label { text: root.categoryText(); color: "#26352f" }
                    Label { text: "終了理由"; font.bold: true; color: "#52605a" }
                    Label { Layout.fillWidth: true; text: root.result.reason_code || "-"; wrapMode: Text.Wrap; color: "#26352f" }
                    Label { text: "ターン数"; font.bold: true; color: "#52605a" }
                    Label { text: root.result.turn_count === undefined ? "-" : root.result.turn_count; color: "#26352f" }
                    Label { text: "battle_select 回数"; font.bold: true; color: "#52605a" }
                    Label { text: root.result.battle_select_count === undefined ? "-" : root.result.battle_select_count; color: "#26352f" }
                    Label { text: "人間の座席 / 先攻後攻"; font.bold: true; color: "#52605a" }
                    Label { text: root.seatRole(); color: "#26352f" }
                    Label { text: "使用デッキ"; font.bold: true; color: "#52605a" }
                    Label { Layout.fillWidth: true; text: root.result.human_deck_name || "-"; wrapMode: Text.Wrap; color: "#26352f" }
                    Label { text: "対戦相手"; font.bold: true; color: "#52605a" }
                    Label {
                        Layout.fillWidth: true
                        text: root.result.submission_id
                              ? "Verified Submission " + root.result.submission_id
                              : "自己管理ローカルエージェント: " + (root.result.artifact_name || "-")
                        wrapMode: Text.Wrap
                        color: "#26352f"
                    }
                    Label { text: "マニフェスト"; font.bold: true; color: "#52605a" }
                    Label { Layout.fillWidth: true; text: root.result.artifact_manifest_id || "-"; wrapMode: Text.Wrap; color: "#26352f" }
                    Label { text: "リプレイ"; font.bold: true; color: "#52605a" }
                    Label {
                        text: controller.replayAvailable && root.result.replay_complete === true
                              ? "完全性確認済み"
                              : "利用不可または不完全"
                        color: controller.replayAvailable ? "#27723c" : "#835f22"
                    }
                    Label { text: "公式ビューワー用JSON"; font.bold: true; color: "#52605a" }
                    Label {
                        Layout.fillWidth: true
                        text: controller.visualizerJsonAvailable
                              ? (controller.visualizerJsonExact ? "保存済み（エンジン出力）" : "保存済み（旧形式から再構成）")
                              : "利用不可"
                        color: controller.visualizerJsonAvailable ? "#27723c" : "#835f22"
                        wrapMode: Text.Wrap
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                text: controller.replayAvailable
                      ? "ワーカー終了とリプレイ完全性を確認しました。"
                      : "完全リプレイは利用できません。"
                color: controller.replayAvailable ? "#27723c" : "#835f22"
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }

            Label {
                objectName: "visualizerJsonNotice"
                Layout.fillWidth: true
                visible: controller.visualizerJsonAvailable
                text: "「" + controller.visualizerJsonFileName + "」を、cg.visualize_data形式を読み込めるビューワーで使用できます。双方の手札、山札順、サイド内容を含むため、外部へ共有しないでください。"
                color: "#7a4c11"
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }

            GridLayout {
                Layout.alignment: Qt.AlignHCenter
                columns: root.width < 760 ? 2 : 3
                rowSpacing: 10
                columnSpacing: 10

                BusyIndicator {
                    running: controller.busy
                    visible: running
                }
                Button {
                    text: "リプレイを開く"
                    highlighted: true
                    enabled: controller.replayAvailable && !controller.busy
                    onClicked: controller.openReplay()
                }
                Button {
                    objectName: "openVisualizerJsonButton"
                    text: "JSONファイルを開く"
                    enabled: controller.visualizerJsonAvailable && !controller.busy
                    onClicked: controller.openVisualizerJson()
                }
                Button {
                    objectName: "openOfficialVisualizerButton"
                    text: "公式ビューワーで見る"
                    enabled: controller.officialVisualizerLauncherAvailable && !controller.busy
                    onClicked: controller.openOfficialVisualizerLauncher()
                }
                Button {
                    objectName: "openReplayFolderButton"
                    text: "保存先を開く"
                    enabled: !controller.busy
                    onClicked: controller.openReplayFolder()
                }
                Button { text: "同じ設定で再戦"; enabled: !controller.busy; onClicked: controller.sameSettingsRematch() }
                Button { text: "座席を入れ替えて再戦"; enabled: !controller.busy; onClicked: controller.swapSeatRematch() }
                Button { text: "診断情報を開く"; enabled: !controller.busy; onClicked: diagnosticsDialog.open() }
                Button { text: "対戦準備へ戻る"; enabled: !controller.busy; onClicked: controller.newMatch() }
            }

            Item { Layout.preferredHeight: 22 }
        }
    }

    Dialog {
        id: diagnosticsDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(720, parent ? parent.width - 36 : 720)
        height: Math.min(540, parent ? parent.height - 36 : 540)
        modal: true
        title: "運用診断情報"
        standardButtons: Dialog.Close

        contentItem: ScrollView {
            TextArea {
                readOnly: true
                wrapMode: Text.WrapAnywhere
                text: JSON.stringify(root.diagnostics, null, 2)
                Accessible.name: "運用診断情報"
            }
        }
    }
}
