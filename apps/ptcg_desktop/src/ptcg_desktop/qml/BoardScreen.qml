import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

FocusScope {
    id: root
    objectName: "boardScreen"
    focus: true
    property var state: controller.stateData || ({})
    property var decision: controller.decisionData || ({})
    property var selectedTokens: []
    property string activeRequestId: ""
    property var previewCard: null

    function containsToken(token) {
        return selectedTokens.indexOf(token) >= 0
    }

    function orderOf(token) {
        return selectedTokens.indexOf(token) + 1
    }

    function optionForToken(token) {
        var options = decision.options || []
        for (var index = 0; index < options.length; ++index) {
            if (options[index].token === token)
                return options[index]
        }
        return null
    }

    function optionForTarget(targetToken) {
        var matches = optionsForTarget(targetToken)
        return matches.length === 1 ? matches[0] : null
    }

    function optionsForTarget(targetToken) {
        var options = decision.options || []
        var matches = []
        for (var index = 0; index < options.length; ++index) {
            if (options[index].target_token === targetToken)
                matches.push(options[index])
        }
        return matches
    }

    function targetChoiceLabel(targetToken) {
        var matches = optionsForTarget(targetToken)
        var numbers = []
        for (var index = 0; index < matches.length; ++index) {
            var option = matches[index]
            var choice = option.choice_number !== undefined ? option.choice_number : index + 1
            numbers.push(String(choice))
        }
        return numbers.join("・")
    }

    function hasNumberedBoardTargets() {
        var options = decision.options || []
        for (var index = 0; index < options.length; ++index) {
            if (options[index].target_token)
                return true
        }
        return false
    }

    function attachmentGuideText() {
        if (decision.context === "context_22")
            return "① つけるエネルギー／カードを選ぶ（現在）　→　② つけるポケモンを選ぶ"
        if (decision.context === "context_21")
            return "① つけるエネルギー／カードを選択済み　→　② つけるポケモンを選ぶ（現在）"
        var options = decision.options || []
        if (options.length > 0) {
            for (var index = 0; index < options.length; ++index) {
                if (options[index].option_type !== 8)
                    return ""
            }
            return "一覧は「つけるカード → ポケモン」の組み合わせです。盤面の番号を見て選んでください。"
        }
        return ""
    }

    function isLegalTarget(targetToken) {
        return targetToken.length > 0 && optionForTarget(targetToken) !== null && !decision.submitting
    }

    function targetSelectionOrder(targetToken) {
        var matches = optionsForTarget(targetToken)
        for (var index = 0; index < matches.length; ++index) {
            var order = orderOf(matches[index].token)
            if (order > 0)
                return order
        }
        return 0
    }

    function toggleToken(token) {
        if (!token || !decision.options || decision.submitting || optionForToken(token) === null)
            return
        var copy = selectedTokens.slice(0)
        var index = copy.indexOf(token)
        if (index >= 0) {
            copy.splice(index, 1)
        } else {
            var maximum = decision.max_count === undefined ? 1 : decision.max_count
            if (maximum === 1)
                copy = [token]
            else if (copy.length < maximum)
                copy.push(token)
        }
        selectedTokens = copy
    }

    function canConfirm() {
        if (!decision.request_id || decision.submitting)
            return false
        var minimum = decision.min_count === undefined ? 0 : decision.min_count
        var maximum = decision.max_count === undefined ? 0 : decision.max_count
        return selectedTokens.length >= minimum && selectedTokens.length <= maximum
    }

    function endsTurn() {
        for (var index = 0; index < selectedTokens.length; ++index) {
            var option = optionForToken(selectedTokens[index])
            if (option && option.kind === "end")
                return true
        }
        return false
    }

    function submitSelection() {
        if (!canConfirm())
            return
        if (endsTurn())
            endTurnDialog.open()
        else
            controller.submitDecision(selectedTokens)
    }

    function phaseText() {
        var values = {
            "PREPARING": "準備中",
            "STARTING": "開始処理中",
            "WAITING_FOR_HUMAN": "あなたの入力待ち",
            "AGENT_THINKING": "AI思考中",
            "ENGINE_PROCESSING": "行動を反映中",
            "FINISHING": "終局処理中",
            "FINISHED": "対戦終了",
            "REPLAY_SEALED": "対戦終了",
            "ABORTED": "異常終了"
        }
        return values[state.phase] || (state.phase || "状態待ち")
    }

    function playerLabel(seat) {
        if (seat !== 0 && seat !== 1)
            return "準備中"
        return seat === state.human_seat ? "あなた" : "AI"
    }

    function defaultPreview() {
        if (state.human && state.human.active && state.human.active.length)
            return state.human.active[0]
        if (state.opponent && state.opponent.active && state.opponent.active.length)
            return state.opponent.active[0]
        return state.stadium || null
    }

    function showPreview(card, active) {
        if (active && card)
            previewCard = card
    }

    onStateChanged: previewCard = null

    onDecisionChanged: {
        var nextId = decision.request_id || ""
        if (nextId !== activeRequestId) {
            activeRequestId = nextId
            selectedTokens = []
            if (nextId.length)
                Qt.callLater(function() { legalList.forceActiveFocus() })
        }
    }

    Connections {
        target: controller
        function onShortcutRequested(token) {
            root.toggleToken(token)
        }
    }

    Shortcut {
        sequence: "Ctrl+Return"
        enabled: root.canConfirm()
        onActivated: root.submitSelection()
    }
    Shortcut {
        sequence: "Ctrl+Enter"
        enabled: root.canConfirm()
        onActivated: root.submitSelection()
    }
    Shortcut {
        sequence: "Escape"
        enabled: root.selectedTokens.length > 0
        onActivated: root.selectedTokens = []
    }
    Shortcut {
        sequence: "F6"
        onActivated: legalList.forceActiveFocus()
    }

    Rectangle {
        anchors.fill: parent
        color: "#76ad65"

        Rectangle {
            anchors.fill: parent
            color: "transparent"
            border.width: 2
            border.color: "#b8d7aa"
        }
    }

    Flickable {
        id: boardScroll
        objectName: "boardScroll"
        anchors.fill: parent
        clip: true
        contentWidth: boardCanvas.width
        contentHeight: boardCanvas.height
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {}
        ScrollBar.horizontal: ScrollBar {}

        Item {
            id: boardCanvas
            width: Math.max(1240, root.width)
            height: Math.max(820, boardLayout.implicitHeight + 16)

            RowLayout {
                id: boardLayout
                anchors.fill: parent
                anchors.margins: 8
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 820
                    spacing: 6

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 42
                        radius: 9
                        color: "#173c2f"
                        border.color: "#8fb89e"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 8
                            spacing: 12
                            Label {
                                text: "Turn " + (root.state.turn === undefined ? "-" : root.state.turn)
                                color: "white"
                                font.pixelSize: 18
                                font.bold: true
                            }
                            Rectangle {
                                implicitWidth: turnLabel.implicitWidth + 18
                                implicitHeight: 27
                                radius: 14
                                color: root.state.acting_seat === root.state.human_seat ? "#f2d56f" : "#6ecf91"
                                Label {
                                    id: turnLabel
                                    anchors.centerIn: parent
                                    text: root.playerLabel(root.state.acting_seat) + "の選択"
                                    color: "#183128"
                                    font.bold: true
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: root.phaseText()
                                color: "#e9f3ee"
                                font.bold: true
                            }
                            Label {
                                text: root.state.first_player === root.state.human_seat ? "先攻: あなた" : "先攻: AI"
                                visible: root.state.first_player === 0 || root.state.first_player === 1
                                color: "#cfddd7"
                                font.pixelSize: 11
                            }
                        }
                    }

                    PlayerField {
                        Layout.fillWidth: true
                        player: root.state.opponent || ({})
                        heading: "AI"
                        panelColor: "#26523f"
                        showHandCards: false
                        selectableForToken: function(token) { return root.isLegalTarget(token) }
                        selectedOrderForToken: function(token) { return root.targetSelectionOrder(token) }
                        choiceLabelForToken: function(token) { return root.targetChoiceLabel(token) }
                        onCardActivated: token => controller.chooseBoardTarget(token)
                        onCardPreviewRequested: (card, active) => root.showPreview(card, active)
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 72
                        radius: 8
                        color: "#6fa75e"
                        border.width: 2
                        border.color: "#d7ead0"

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 5
                            spacing: 8
                            Rectangle { Layout.fillWidth: true; height: 3; color: "#e7f1e1"; radius: 2 }
                            Label {
                                text: "スタジアム"
                                color: "#17372b"
                                font.bold: true
                            }
                            CardTile {
                                Layout.preferredWidth: 48
                                Layout.preferredHeight: 66
                                card: root.state.stadium || null
                                compact: true
                                selectable: root.state.stadium
                                            ? root.isLegalTarget(root.state.stadium.state_token || "") : false
                                selectedOrder: root.state.stadium
                                               ? root.targetSelectionOrder(root.state.stadium.state_token || "") : 0
                                choiceLabel: root.state.stadium
                                             ? root.targetChoiceLabel(root.state.stadium.state_token || "") : ""
                                onActivated: token => controller.chooseBoardTarget(token)
                                onPreviewRequested: (card, active) => root.showPreview(card, active)
                            }
                            Label {
                                text: root.state.stadium
                                      ? controller.cardName(root.state.stadium.card_id, root.state.stadium.fallback_name)
                                      : "なし"
                                color: "#17372b"
                                font.bold: true
                                Layout.preferredWidth: 140
                                elide: Text.ElideRight
                            }
                            Rectangle { Layout.fillWidth: true; height: 3; color: "#e7f1e1"; radius: 2 }
                        }
                    }

                    PlayerField {
                        Layout.fillWidth: true
                        player: root.state.human || ({})
                        heading: "あなた"
                        panelColor: "#1e4c39"
                        showHandCards: true
                        selectableForToken: function(token) { return root.isLegalTarget(token) }
                        selectedOrderForToken: function(token) { return root.targetSelectionOrder(token) }
                        choiceLabelForToken: function(token) { return root.targetChoiceLabel(token) }
                        onCardActivated: token => controller.chooseBoardTarget(token)
                        onCardPreviewRequested: (card, active) => root.showPreview(card, active)
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 390
                    Layout.fillHeight: true
                    Layout.minimumHeight: 800
                    radius: 12
                    color: "#f4f1e7"
                    border.width: 2
                    border.color: "#315c4c"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 8
                        spacing: 7

                        CardPreview {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 500
                            card: root.previewCard || root.defaultPreview()
                        }

                        Rectangle {
                            id: actionPanel
                            objectName: "latestActionPanel"
                            property int observedRevision: controller.latestActionRevision
                            Layout.fillWidth: true
                            implicitHeight: actionColumn.implicitHeight + 16
                            radius: 9
                            color: controller.latestActionTitle === "AIの行動" ? "#fff0bd" : "#e4f0e8"
                            border.width: 2
                            border.color: controller.latestActionTitle === "AIの行動" ? "#bf7c16" : "#477660"
                            onObservedRevisionChanged: actionFlash.restart()

                            SequentialAnimation {
                                id: actionFlash
                                NumberAnimation { target: actionPanel; property: "opacity"; from: 0.35; to: 1.0; duration: 240 }
                            }

                            ColumnLayout {
                                id: actionColumn
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 3
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label {
                                        text: controller.latestActionTitle
                                        color: "#22372e"
                                        font.bold: true
                                    }
                                    Item { Layout.fillWidth: true }
                                    Label {
                                        text: root.phaseText()
                                        color: "#56685f"
                                        font.pixelSize: 11
                                    }
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: controller.latestActionText
                                    color: "#26352f"
                                    font.pixelSize: 13
                                    font.bold: controller.latestActionTitle === "AIの行動"
                                    wrapMode: Text.Wrap
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 9
                            color: "#fffdf5"
                            border.color: "#b6beb8"

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 7
                                spacing: 5

                                Label {
                                    Layout.fillWidth: true
                                    text: root.decision.prompt || "AIの行動を待っています。"
                                    color: "#1f2d28"
                                    font.pixelSize: 15
                                    font.bold: true
                                    wrapMode: Text.Wrap
                                }

                                Label {
                                    visible: !!root.decision.request_id
                                    Layout.fillWidth: true
                                    text: "選択 " + root.selectedTokens.length
                                          + " / " + root.decision.min_count + "～" + root.decision.max_count
                                    color: "#52635b"
                                    font.pixelSize: 11
                                }

                                Rectangle {
                                    id: attachmentStepGuide
                                    objectName: "attachmentStepGuide"
                                    visible: root.attachmentGuideText().length > 0
                                    Layout.fillWidth: true
                                    implicitHeight: attachmentStepText.implicitHeight + 12
                                    radius: 7
                                    color: "#e8f5ec"
                                    border.color: "#63a87b"

                                    Label {
                                        id: attachmentStepText
                                        objectName: "attachmentStepText"
                                        anchors.fill: parent
                                        anchors.margins: 6
                                        text: root.attachmentGuideText()
                                        color: "#174c2b"
                                        font.pixelSize: 11
                                        font.bold: true
                                        wrapMode: Text.Wrap
                                    }
                                }

                                Label {
                                    visible: !!root.decision.request_id && root.hasNumberedBoardTargets()
                                    Layout.fillWidth: true
                                    text: "一覧の番号は盤面カード左上の番号と対応します。選択するとカード全体が金色になります。"
                                    color: "#31584a"
                                    font.pixelSize: 11
                                    wrapMode: Text.Wrap
                                }

                                ListView {
                                    id: legalList
                                    objectName: "legalList"
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.minimumHeight: 118
                                    model: root.decision.options || []
                                    spacing: 4
                                    clip: true
                                    activeFocusOnTab: true
                                    keyNavigationEnabled: true
                                    currentIndex: count > 0 ? 0 : -1
                                    enabled: root.decision.submitting !== true
                                    Accessible.name: "合法手の選択肢"

                                    delegate: Button {
                                        objectName: "legalOptionButton"
                                        required property var modelData
                                        required property int index
                                        width: legalList.width
                                        height: 58
                                        checkable: true
                                        checked: root.containsToken(modelData.token)
                                        focus: ListView.isCurrentItem
                                        text: (checked ? "✓ " : "")
                                              + (modelData.choice_number !== undefined ? modelData.choice_number : index + 1)
                                              + "　" + modelData.label
                                              + (modelData.detail ? "\n" + modelData.detail : "")
                                        font.bold: checked
                                        onClicked: root.toggleToken(modelData.token)
                                        Keys.onReturnPressed: root.toggleToken(modelData.token)
                                        Keys.onEnterPressed: root.toggleToken(modelData.token)
                                        Accessible.description: checked
                                                                ? "選択順 " + root.orderOf(modelData.token)
                                                                : "未選択。SpaceまたはEnterで選択"
                                    }

                                    Keys.onSpacePressed: {
                                        if (currentItem)
                                            root.toggleToken(currentItem.modelData.token)
                                    }
                                }

                                Label {
                                    visible: root.decision.submitting === true
                                    Layout.fillWidth: true
                                    text: "選択を送信しました。反映を待っています…"
                                    color: "#835f22"
                                    wrapMode: Text.Wrap
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    Button {
                                        text: "解除"
                                        enabled: root.selectedTokens.length > 0 && !root.decision.submitting
                                        onClicked: root.selectedTokens = []
                                    }
                                    Button {
                                        id: confirmButton
                                        objectName: "confirmDecisionButton"
                                        Layout.fillWidth: true
                                        text: root.decision.min_count === 0 && root.selectedTokens.length === 0
                                              ? "選択せず確定" : "選択を決定"
                                        highlighted: true
                                        enabled: root.canConfirm()
                                        onClicked: root.submitSelection()
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                Layout.fillWidth: true
                                text: "F6: 選択肢  /  Ctrl+Enter: 決定"
                                color: "#5f6d67"
                                font.pixelSize: 10
                            }
                            Button {
                                text: "対戦を放棄"
                                enabled: root.state.result === -1
                                         && ["FINISHING", "FINISHED", "REPLAY_SEALED", "ABORTED"].indexOf(root.state.phase) < 0
                                onClicked: forfeitDialog.open()
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: endTurnDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        title: "番を終了しますか？"
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: controller.submitDecision(root.selectedTokens)
    }

    Dialog {
        id: forfeitDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        title: "対戦を放棄しますか？"
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: controller.forfeit()
    }
}
