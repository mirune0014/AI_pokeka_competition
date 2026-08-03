import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

FocusScope {
    id: root
    property var artifact: controller.artifactDetails || ({})
    property var fingerprint: artifact.environment_fingerprint || ({})

    Rectangle { anchors.fill: parent; color: "#f3f1eb" }

    ScrollView {
        anchors.fill: parent
        contentWidth: Math.max(620, availableWidth)

        ColumnLayout {
            width: Math.min(980, Math.max(580, root.width - 48))
            x: Math.max(20, (Math.max(620, root.width) - width) / 2)
            spacing: 18

            Item { Layout.preferredHeight: 14 }

            Label {
                text: "PTCG Human Client"
                color: "#18372e"
                font.pixelSize: 30
                font.bold: true
            }

            Label {
                text: controller.canStart && controller.verifiedMatch
                      ? "保存済み submission 55155015 とのバイト一致と起動互換性を確認済みです。"
                      : (controller.canStart && controller.localAgentRegistered
                         ? "自分で管理するローカルエージェントの登録内容と起動互換性を確認済みです。"
                         : (controller.artifactReady
                            ? "エージェントは登録済みです。デッキまたは起動互換性を確認してください。"
                            : "ローカルエージェントと人間デッキを選択し、内容を登録して互換性を確認してください。"))
                color: "#4c5b55"
                font.pixelSize: 15
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            GroupBox {
                title: "1. 対戦相手エージェント"
                enabled: !controller.busy
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 9

                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            Layout.fillWidth: true
                            text: controller.artifactPath
                            readOnly: true
                            placeholderText: "main.py、deck.csv、cg がある .tar.gz または実行ルート"
                            Accessible.name: "ローカルエージェントパス"
                        }
                        Button {
                            objectName: "browseArtifactArchiveButton"
                            text: "tar.gzファイル…"
                            Accessible.name: "tar.gzエージェントファイルを選択"
                            onClicked: controller.browseArtifactArchive()
                        }
                        Button {
                            objectName: "browseArtifactFolderButton"
                            text: "展開済みフォルダー…"
                            Accessible.name: "展開済みエージェントフォルダーを選択"
                            onClicked: controller.browseArtifactFolder()
                        }
                    }

                    Label {
                        objectName: "artifactPickerHelp"
                        text: "圧縮された提出物は「tar.gzファイル…」を選びます。「展開済みフォルダー…」ではファイルは表示されません。"
                        color: "#59655f"
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Label {
                        text: controller.artifactStatus
                        color: controller.artifactReady ? "#21743a" : "#805f23"
                        font.bold: true
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        StatusPill {
                            text: controller.verifiedMatch ? "submission 55155015 バイト一致" : "自己管理コード（安全性未審査）"
                            ok: controller.verifiedMatch
                            warning: controller.localAgentRegistered
                        }
                        StatusPill { text: "登録内容と一致"; ok: controller.artifactReady }
                        StatusPill { text: "起動互換性確認済み"; ok: controller.deckStatus.engine === true }
                        StatusPill { text: "Windows x64環境"; ok: artifact.environment_supported === true }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "登録ID: " + (artifact.manifest_id || "-")
                              + "\nパッケージ内容 SHA-256: " + (artifact.content_sha256 || "-")
                              + "\n登録ファイル数: " + (artifact.file_count === undefined ? "-" : artifact.file_count)
                              + " / 環境: " + (fingerprint.os || "-") + " " + (fingerprint.os_release || "")
                              + " / " + (fingerprint.machine || "-")
                              + " / CPython " + (fingerprint.python_version || "-") + " " + (fingerprint.python_bits || "-") + "bit"
                        color: "#59655f"
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                    }

                    Label {
                        text: "選択した Python コードとネイティブ DLL を対戦用子プロセスで実行します。この子プロセスは OS サンドボックスではありません。自分で管理し、内容を確認したコードだけを登録してください。ファイル構成または内容が変わると、再登録するまで開始できません。\n起動互換性の確認は、すべての局面での正常動作やコードの安全性を保証しません。"
                        color: "#67736e"
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }

            GroupBox {
                title: "2. 人間の 60 枚デッキ"
                enabled: !controller.busy
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            Layout.fillWidth: true
                            text: controller.deckPath
                            readOnly: true
                            placeholderText: "UTF-8 CSV"
                            Accessible.name: "デッキ CSV パス"
                        }
                        Button { text: "選択…"; onClicked: controller.browseDeck() }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        StatusPill { text: "60枚構成確認済み"; ok: controller.deckStatus.structure === true }
                        StatusPill { text: "両座席でエンジン受理確認済み"; ok: controller.deckStatus.engine === true }
                        StatusPill { text: "大会レギュレーション未検証"; warning: true }
                    }

                    Label {
                        visible: controller.deckStatus.cards && controller.deckStatus.cards.length > 0
                        Layout.fillWidth: true
                        text: {
                            var rows = []
                            var cards = controller.deckStatus.cards || []
                            for (var i = 0; i < cards.length; ++i)
                                rows.push(cards[i].count + " × " + cards[i].name + " (#" + cards[i].card_id + ")")
                            return "日本語デッキ一覧:  " + rows.join(" / ")
                        }
                        wrapMode: Text.Wrap
                        color: "#394a43"
                    }
                }
            }

            GroupBox {
                title: "3. 席・時間・ローカル表示"
                enabled: !controller.busy
                Layout.fillWidth: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10

                    Flow {
                        Layout.fillWidth: true
                        spacing: 10
                        Label { text: "人間の席:"; font.bold: true }
                        RadioButton { text: "Player 0"; checked: controller.humanSeat === 0; onClicked: controller.setHumanSeat(0) }
                        RadioButton { text: "Player 1"; checked: controller.humanSeat === 1; onClicked: controller.setHumanSeat(1) }
                        RadioButton { text: "ランダム"; checked: controller.humanSeat === -1; onClicked: controller.setHumanSeat(-1) }
                    }

                    Label {
                        text: "先攻・後攻は座席とは別に、ゲーム内の通常選択で決まります。"
                        color: "#5b6863"
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "AI行動の表示時間（ms）"; Layout.preferredWidth: 190 }
                        SpinBox {
                            from: 400; to: 10000; stepSize: 100; editable: true
                            value: controller.aiDisplayDelayMs
                            onValueModified: controller.setAiDisplayDelayMs(value)
                            Accessible.name: "AI行動の表示時間"
                        }
                        Label { Layout.fillWidth: true; text: "AIの各行動を盤面に残す時間です。標準は1000msで、判断内容には影響しません。"; color: "#67736e"; wrapMode: Text.Wrap }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "AI応答タイムアウト（秒）"; Layout.preferredWidth: 190 }
                        SpinBox {
                            from: 1; to: 600; editable: true
                            value: controller.agentTimeoutSeconds
                            onValueModified: controller.setAgentTimeoutSeconds(value)
                            Accessible.name: "AI応答タイムアウト"
                        }
                        Label { Layout.fillWidth: true; text: "異常判定に使用します。"; color: "#67736e" }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            Layout.fillWidth: true
                            text: controller.imageFolder
                            readOnly: true
                            placeholderText: "任意: ローカルの日本語カード画像フォルダー"
                            Accessible.name: "カード画像フォルダー"
                        }
                        Button { text: "画像…"; onClicked: controller.browseImages() }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            Layout.fillWidth: true
                            text: controller.replayFolder
                            readOnly: true
                            Accessible.name: "リプレイ保存フォルダー"
                        }
                        Button { text: "保存先…"; onClicked: controller.browseReplayFolder() }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                BusyIndicator { running: controller.busy; visible: running }
                Button {
                    text: controller.busy ? "登録・確認中…" : "この内容を登録して互換性を確認"
                    enabled: !controller.busy && controller.artifactPath.length > 0 && controller.deckPath.length > 0
                    onClicked: controller.verifySetup()
                }
                Button {
                    text: controller.verifiedMatch ? "Verified Match を開始" : "ローカル対戦を開始"
                    highlighted: true
                    enabled: controller.canStart
                    onClicked: controller.startMatch()
                }
            }

            Item { Layout.preferredHeight: 20 }
        }
    }
}
