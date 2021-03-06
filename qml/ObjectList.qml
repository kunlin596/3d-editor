import QtQuick 2.0


Rectangle {
    id: object_list
    width: 100

    gradient: static_color
    Gradient {
        id: static_color
        GradientStop { position: 0.0; color: Qt.rgba(0.2, 0.2, 0.2, 0.8)}
        GradientStop { position: 0.66; color: Qt.rgba(0.1, 0.1, 0.1, 0.8)}
        GradientStop { position: 1.0; color: Qt.rgba(0.1, 0.1, 0.1, 0.8)}
    }

    ListView {
        id: listView
        width: 100
        anchors.fill:parent
        clip: true

        model: listModel
        delegate: MyButton {
            text: hour
        }
    }

    Image {
        id: menu_image_shadow
        anchors.top: parent.top
        anchors.left: parent.right
        height: parent.height
        z: 4
        source: "shadow_long.png"
    }

    ListModel {
        id: listModel
        Component.onCompleted: {
            for (var i = 0; i < 10; i++) {
                append(createListElement(i));
            }
        }
        function createListElement(i) {
            return {
                hour: i
            };
        }
    }

    states: [
        State{
            name: "Visible"
            PropertyChanges{target: object_list; opacity: 1.0}
            PropertyChanges{target: object_list; visible: true}
        },
        State{
            name: "Invisible"
            PropertyChanges{target: object_list; opacity: 0.0}
            PropertyChanges{target: object_list; visible: false}
        }
    ]
    transitions: [
        Transition {
            from: "Visible"
            to: "Invisible"

            SequentialAnimation{
               NumberAnimation {
                   target: object_list
                   property: "opacity"
                   duration: 200
                   easing.type: Easing.InOutQuad
               }
               NumberAnimation {
                   target: object_list
                   property: "visible"
                   duration: 0
               }
            }
        },
        Transition {
            from: "Invisible"
            to: "Visible"
            SequentialAnimation{
               NumberAnimation {
                   target: object_list
                   property: "visible"
                   duration: 0
               }
               NumberAnimation {
                   target: object_list
                   property: "opacity"
                   duration: 200
                   easing.type: Easing.InOutQuad
               }
            }
        }
    ]
}