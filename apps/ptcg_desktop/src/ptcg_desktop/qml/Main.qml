import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: Math.max(640, Math.min(1440, Screen.desktopAvailableWidth))
    height: Math.max(360, Math.min(900, Screen.desktopAvailableHeight))
    minimumWidth: 640
    minimumHeight: 360
    visible: true
    title: "PTCG Human Client"
    font.family: "Yu Gothic UI"
    color: "#f1efe8"

    StackLayout {
        anchors.fill: parent
        currentIndex: controller.screen === "setup" ? 0 : (controller.screen === "board" ? 1 : (controller.screen === "result" ? 2 : 3))

        SetupScreen { Layout.fillWidth: true; Layout.fillHeight: true }
        BoardScreen { Layout.fillWidth: true; Layout.fillHeight: true }
        ResultScreen { Layout.fillWidth: true; Layout.fillHeight: true }
        ReplayScreen { Layout.fillWidth: true; Layout.fillHeight: true }
    }

    Rectangle {
        visible: controller.errorText.length > 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: errorLabel.implicitHeight + 20
        color: "#a53c36"
        z: 100
        Label {
            id: errorLabel
            anchors.centerIn: parent
            width: parent.width - 40
            text: controller.errorText
            color: "white"
            font.bold: true
            wrapMode: Text.Wrap
            horizontalAlignment: Text.AlignHCenter
        }
    }
}
