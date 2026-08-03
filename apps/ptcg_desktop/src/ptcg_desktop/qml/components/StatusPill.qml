import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    property string text: ""
    property bool ok: false
    property bool warning: false
    implicitWidth: label.implicitWidth + 22
    implicitHeight: 30
    radius: 15
    color: ok ? "#d9f4df" : (warning ? "#fff1c7" : "#e8ecea")
    border.color: ok ? "#4a9b5d" : (warning ? "#c18a28" : "#8a9992")

    Label {
        id: label
        anchors.centerIn: parent
        text: (root.ok ? "✓ " : (root.warning ? "! " : "· ")) + root.text
        color: root.ok ? "#1d6630" : (root.warning ? "#74500e" : "#46524d")
        font.pixelSize: 13
        font.bold: true
    }
}
