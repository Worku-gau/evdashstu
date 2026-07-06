import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    width: 1024
    height: 600
    visible: true
    title: "EV Dashboard - MQTT Client"
    color: "#111111"

    // =================================================
    // 1. BACKGROUND
    // =================================================
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop {
                position: 0.0
                color: "#141414"
            }
            GradientStop {
                position: 0.5
                color: "#1A1A1A"
            }
            GradientStop {
                position: 1.0
                color: "#0A0A0A"
            }
        }
    }

    // Vignette
    Rectangle {
        anchors.fill: parent
        color: "transparent"

        Rectangle {
            width: parent.width
            height: 100
            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: "#aa000000"
                }
                GradientStop {
                    position: 1.0
                    color: "transparent"
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 100
            anchors.bottom: parent.bottom
            gradient: Gradient {
                GradientStop {
                    position: 0.0
                    color: "transparent"
                }
                GradientStop {
                    position: 1.0
                    color: "#aa000000"
                }
            }
        }
    }

    // =================================================
    // 2. COMPONENTS
    // =================================================
    component DashboardIcon: Image {
        property bool active: false

        Layout.preferredWidth: 32
        Layout.preferredHeight: 32
        sourceSize.width: 32
        sourceSize.height: 32
        fillMode: Image.PreserveAspectFit
        smooth: true

        opacity: active ? 1.0 : 0.15

        Behavior on opacity {
            NumberAnimation { duration: 200 }
        }
    }

    component LightBulb: Item {
        property color lightColor: "#FFFFFF"
        property bool active: false

        opacity: active ? 1.0 : 0.0
        Behavior on opacity {
            NumberAnimation {
                duration: 100
            }
        }

        // Core Light
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.8
            height: parent.height * 0.8
            radius: width/2
            color: lightColor
        }

        // Bloom Glow
        Canvas {
            anchors.centerIn: parent
            width: parent.width * 3.0
            height: parent.height * 3.0
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0,0,width,height)
                var grad = ctx.createRadialGradient(width/2, height/2, 0, width/2, height/2, width/2)
                grad.addColorStop(0, Qt.rgba(lightColor.r, lightColor.g, lightColor.b, 0.6))
                grad.addColorStop(1, "transparent")
                ctx.fillStyle = grad
                ctx.fillRect(0,0,width,height)
            }
        }
    }

    // =================================================
    // 3. TOP BAR
    // =================================================
    Item {
        id: topBar
        height: 60
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right

        Row {
            anchors.centerIn: parent
            spacing: 20
            Text {
                text: Qt.formatTime(new Date(), "hh:mm") // Local time fallback
                color: "#888"
                font.pixelSize: 16
                font.bold: true
            }
            Text {
                text: Qt.formatDate(new Date(), "ddd MMM d")
                color: "#CCC"
                font.pixelSize: 16
                font.bold: true
            }
            Text {
                text: "24°C" // You can bind this to vehicleState.temp if available
                color: "#CCC"
                font.pixelSize: 16
                font.bold: true
            }
        }

        RowLayout {
            anchors.right: parent.right
            anchors.rightMargin: 40
            anchors.verticalCenter: parent.verticalCenter
            spacing: 15

            DashboardIcon {
                source: "assets/icons/ev/battery_low.svg"
                active: vehicleState.batteryLow
            }
            DashboardIcon {
                source: "assets/icons/safety/door_open.svg"
                active: vehicleState.doorOpen
            }
            DashboardIcon {
                source: "assets/icons/brakes/parking_brake.svg"
                active: vehicleState.parkingBrake
            }
            DashboardIcon {
                source: "assets/icons/brakes/abs.svg"
                active: vehicleState.absWarn
            }
            DashboardIcon {
                source: "assets/icons/ev/hv_fault.svg"
                active: vehicleState.fault
            }
        }
    }

    // =================================================
    // 4. MAIN LAYOUT
    // =================================================
    RowLayout {
        anchors.top: topBar.bottom
        anchors.bottom: bottomBar.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: 40
        anchors.rightMargin: 40
        spacing: 20

        // LEFT ZONE (GEAR & POWER)
        Item {
            Layout.preferredWidth: 250
            Layout.fillHeight: true

            Column {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -20
                spacing: 10

                // Active Gear Display
                Text {
                    text: vehicleState.gear
                    color: "#5BC0EB"
                    font.pixelSize: 120
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                // Charging Indicator
                Column {
                    visible: vehicleState.charging
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 5

                    Text {
                        text: "CHARGING"
                        color: "#2ECC71"
                        font.bold: true
                        font.pixelSize: 18
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                    Text {
                        text: vehicleState.soc + "%"
                        color: "#FFF"
                        font.bold: true
                        font.pixelSize: 40
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    SequentialAnimation on opacity {
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.5; duration: 1000 }
                        NumberAnimation { to: 1.0; duration: 1000 }
                    }
                }

                // Gear List
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.horizontalCenterOffset: 8
                    spacing: 15
                    Text {
                        text: "P"
                        color: vehicleState.gear == "P" ? "#FFF" : "#444"
                        font.pixelSize: 24
                        font.bold: true
                    }
                    Text {
                        text: "R"
                        color: vehicleState.gear == "R" ? "#D0021B" : "#444"
                        font.pixelSize: 24
                        font.bold: true
                    }
                    Text {
                        text: "N"
                        color: vehicleState.gear == "N" ? "#FFF" : "#444"
                        font.pixelSize: 24
                        font.bold: true
                    }
                    Text {
                        text: "D"
                        color: vehicleState.gear == "D" ? "#5BC0EB" : "#444"
                        font.pixelSize: 24
                        font.bold: true
                    }
                }
            }

            // Power Canvas
            Canvas {
                id: powerBarCanvas
                visible: !vehicleState.charging
                anchors.fill: parent
                property real smoothPower: 0
                property real targetPower: vehicleState.power

                Behavior on smoothPower {
                    NumberAnimation {
                        duration: 100
                        easing.type: Easing.Linear
                    }
                }
                onTargetPowerChanged: smoothPower = targetPower
                onSmoothPowerChanged: requestPaint()

                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0,0,width,height)
                    var barWidth = 18
                    var startX = 60
                    var startY = 60
                    var bottomY = height - 60
                    var curveRadius = 70
                    var cornerY = bottomY - curveRadius

                    // Track
                    ctx.lineCap = "round"
                    ctx.lineJoin = "round"
                    ctx.lineWidth = barWidth
                    ctx.beginPath()
                    ctx.moveTo(startX, startY)
                    ctx.lineTo(startX, cornerY)
                    ctx.quadraticCurveTo(startX, bottomY, startX + curveRadius * 2.0, bottomY)
                    ctx.strokeStyle = "#222"
                    ctx.stroke()

                    // Active Fill
                    ctx.lineWidth = barWidth

                    if (smoothPower >= 0) {
                        var maxH = cornerY - startY
                        var clamped = Math.min(smoothPower, 150.0)
                        var currentH = (clamped / 150.0) * maxH

                        var grad = ctx.createLinearGradient(0, cornerY - currentH, 0, cornerY)
                        grad.addColorStop(0, "#FFD700")
                        grad.addColorStop(1, "#FF8C00")
                        ctx.strokeStyle = grad

                        ctx.beginPath()
                        ctx.moveTo(startX, cornerY)
                        ctx.lineTo(startX, cornerY - currentH)
                        ctx.lineCap = "butt"
                        ctx.stroke()

                        if(currentH > 0) {
                            ctx.fillStyle = "#FFD700"
                            ctx.beginPath()
                            ctx.arc(startX, cornerY - currentH, barWidth/2, 0, Math.PI*2)
                            ctx.fill()
                        }
                    } else {
                        var reg = Math.abs(smoothPower)
                        var t = reg / 50.0
                        if (t > 1.0) t = 1.0

                        ctx.strokeStyle = "#2ECC71"
                        var p0x = startX
                        var p0y = cornerY
                        var p1x = startX
                        var p1y = bottomY
                        var p2x = startX + curveRadius * 2.0
                        var p2y = bottomY

                        var destX = (1-t)*(1-t)*p0x + 2*(1-t)*t*p1x + t*t*p2x
                        var destY = (1-t)*(1-t)*p0y + 2*(1-t)*t*p1y + t*t*p2y
                        var cpX = startX
                        var cpY = cornerY + (bottomY - cornerY) * t

                        ctx.beginPath()
                        ctx.moveTo(startX, cornerY)
                        ctx.quadraticCurveTo(cpX, destY, destX, destY)
                        ctx.lineCap = "butt"
                        ctx.stroke()

                        ctx.fillStyle = "#2ECC71"
                        ctx.beginPath()
                        ctx.arc(destX, destY, barWidth/2, 0, Math.PI*2)
                        ctx.fill()
                    }

                    ctx.beginPath()
                    ctx.moveTo(startX - 12, cornerY)
                    ctx.lineTo(startX + 12, cornerY)
                    ctx.lineWidth = 2
                    ctx.strokeStyle = "#FFFFFF"
                    ctx.lineCap = "butt"
                    ctx.stroke()

                    ctx.fillStyle = "#888"
                    ctx.font = "12px Arial"
                    ctx.fillText("PWR", startX + 25, startY + 10)
                    ctx.fillText("CHG", startX + 70, bottomY - 15)
                }
            }
        }

        // CENTER ZONE
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Speedometer (Hidden when Charging)
            Item {
                visible: !vehicleState.charging
                anchors.fill: parent
                Text {
                    text: vehicleState.speed
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    // MOVED UP by 10px (previous was 40, now 30)
                    anchors.topMargin: 30
                    color: "#FFF"
                    font.pixelSize: 100
                    font.bold: true
                    style: Text.Outline
                    styleColor: "#000"
                }
                Text {
                    text: "km/h"
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    // MOVED UP by 10px (previous was 150, now 140)
                    anchors.topMargin: 140
                    color: "#666"
                    font.pixelSize: 16
                }
            }

            // Charging Status
            Text {
                visible: vehicleState.charging
                text: "CONNECTED"
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -50
                color: "#2ECC71"
                font.pixelSize: 40
                font.bold: true
                opacity: 0.8
            }

            // 3D Stage
            Item {
                width: 300
                height: 300
                anchors.centerIn: parent
                anchors.verticalCenterOffset: 60

                // Road Animation
                Item {
                    id: roadLayer
                    visible: !vehicleState.charging
                    width: 240
                    height: 300
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: 50
                    z: -1
                    opacity: 0.5

                    transform: Rotation {
                        origin.x: 120
                        origin.y: 0
                        axis { x: 1; y: 0; z: 0 }
                        angle: 45
                    }

                    property real offset: 0
                    property int cycleSize: 60 // The Common Multiple

                    Timer {
                        interval: 16
                        running: true
                        repeat: true
                        onTriggered: {
                            var speedFactor = vehicleState.speed * 0.15

                            if (vehicleState.gear === "R") {
                                parent.offset -= speedFactor
                                if (parent.offset < 0) parent.offset = parent.cycleSize
                            } else {
                                parent.offset += speedFactor
                                if (parent.offset > parent.cycleSize) parent.offset = 0
                            }
                        }
                    }

                    // --- JAGGED FIX: Unified Spacing and Heights ---

                    // Left Edge
                    Column {
                        x: 0
                        y: -roadLayer.cycleSize + roadLayer.offset
                        spacing: 30 // Gap
                        Repeater {
                            model: 10 // Enough coverage
                            Rectangle {
                                width: 6
                                height: 30 // Dash
                                color: "#555"
                                radius: 2
                            }
                        }
                    }

                    // Center Line
                    Column {
                        anchors.horizontalCenter: parent.horizontalCenter
                        y: -roadLayer.cycleSize + roadLayer.offset
                        spacing: 40 // Gap
                        Repeater {
                            model: 10
                            Rectangle {
                                width: 4
                                height: 20 // Dash (20 + 40 = 60px Cycle)
                                color: "#888"
                                radius: 2
                            }
                        }
                    }

                    // Right Edge
                    Column {
                        x: parent.width - 6
                        y: -roadLayer.cycleSize + roadLayer.offset
                        spacing: 30 // Gap
                        Repeater {
                            model: 10
                            Rectangle {
                                width: 6
                                height: 30 // Dash (30 + 30 = 60px Cycle)
                                color: "#555"
                                radius: 2
                            }
                        }
                    }
                }

                // Car Shadow (Requested: Darker)
                Canvas {
                    width: 180
                    height: 100
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: 15
                    opacity: 1.0
                    onPaint: {
                        var ctx = getContext("2d")
                        var g = ctx.createRadialGradient(width/2,height/2,0,width/2,height/2,width/2)
                        // Pitch black center, fading out
                        g.addColorStop(0,"#CC000000")
                        g.addColorStop(0.6,"#88000000")
                        g.addColorStop(1,"transparent")
                        ctx.fillStyle=g
                        ctx.fillRect(0,0,width,height)
                    }
                }

                // Headlight Beams
                Item {
                    visible: !vehicleState.charging && vehicleState.highBeam
                    width: 240
                    height: 200
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: -80
                    z: -1
                    opacity: 0.4

                    Rectangle {
                        width: 60
                        height: 180
                        rotation: -10
                        x: 60
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: "#5BC0EB" }
                        }
                    }
                    Rectangle {
                        width: 60
                        height: 180
                        rotation: 10
                        x: 120
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "transparent" }
                            GradientStop { position: 1.0; color: "#5BC0EB" }
                        }
                    }
                }

                // Car Body & Lights
                Item {
                    visible: !vehicleState.charging
                    width: 200
                    height: 160
                    anchors.centerIn: parent
                    scale: vehicleState.brakes ? 0.97 : 1.0
                    Behavior on scale {
                        NumberAnimation {
                            duration: 250
                            easing.type: Easing.OutQuad
                        }
                    }

                    Image {
                        anchors.fill: parent
                        source: "assets/car_top.png"
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }

                    // Headlights
                    LightBulb {
                        width: 15; height: 10
                        x: 65; y: 12
                        lightColor: "#5BC0EB"
                        active: vehicleState.highBeam || vehicleState.lowBeam
                    }
                    LightBulb {
                        width: 15; height: 10
                        x: 120; y: 12
                        lightColor: "#5BC0EB"
                        active: vehicleState.highBeam || vehicleState.lowBeam
                    }

                    // Brake Lights
                    LightBulb {
                        width: 30; height: 8
                        x: 65; y: 145
                        lightColor: "#D0021B"
                        active: vehicleState.brakes
                    }
                    LightBulb {
                        width: 30; height: 8
                        x: 105; y: 145
                        lightColor: "#D0021B"
                        active: vehicleState.brakes
                    }

                    // Indicators
                    LightBulb {
                        width: 10; height: 10
                        x: 52; y: 55
                        lightColor: "#FF9500"
                        active: vehicleState.leftTurn
                    }
                    LightBulb {
                        width: 10; height: 10
                        x: 138; y: 55
                        lightColor: "#FF9500"
                        active: vehicleState.rightTurn
                    }
                }
            }
        }

        // RIGHT ZONE
        Item {
            Layout.preferredWidth: 250
            Layout.fillHeight: true

            Canvas {
                id: batteryCircle
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0,0,width,height)
                    var cx = width/2
                    var cy = height/2
                    var r = 80

                    ctx.lineCap = "round"
                    ctx.lineWidth = 14

                    ctx.beginPath()
                    ctx.arc(cx,cy,r, Math.PI*0.8, Math.PI*2.2)
                    ctx.strokeStyle = "#1A1A1A"
                    ctx.stroke()

                    var grad = ctx.createLinearGradient(0, 0, width, 0)
                    grad.addColorStop(0, "#2ECC71")
                    grad.addColorStop(1, "#27AE60")

                    var end = Math.PI*0.8 + ( (Math.PI*1.4) * (vehicleState.soc/100.0) )

                    ctx.beginPath()
                    ctx.arc(cx,cy,r, Math.PI*0.8, end)
                    ctx.strokeStyle = grad
                    ctx.stroke()
                }
                Connections {
                    target: vehicleState
                    function onSocChanged() { batteryCircle.requestPaint() }
                }
            }

            Column {
                anchors.centerIn: parent
                Text {
                    text: vehicleState.range + " km"
                    color: "white"
                    font.pixelSize: 32
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: vehicleState.soc + "%"
                    color: "#AAA"
                    font.pixelSize: 18
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }

            Text {
                text: "Battery Level"
                anchors.horizontalCenter: parent.horizontalCenter
                // MOVED RIGHT by 20px
                anchors.horizontalCenterOffset: 20
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 60
                color: "#2ECC71"
                font.pixelSize: 14
            }
        }
    }

    // =================================================
    // 5. BOTTOM BAR
    // =================================================
    Item {
        id: bottomBar
        height: 80
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right

        RowLayout {
            anchors.left: parent.left
            anchors.leftMargin: 40
            anchors.verticalCenter: parent.verticalCenter
            spacing: 20

            DashboardIcon {
                source: "assets/icons/lighting/indicator_left.svg"
                active: vehicleState.leftTurn
            }
            DashboardIcon {
                source: "assets/icons/lighting/low_beam.svg"
                active: vehicleState.lowBeam
            }
            DashboardIcon {
                source: "assets/icons/lighting/high_beam.svg"
                active: vehicleState.highBeam
            }
            DashboardIcon {
                source: "assets/icons/lighting/fog_front.svg"
                active: vehicleState.fogFront
            }
        }

        RowLayout {
            anchors.right: parent.right
            anchors.rightMargin: 40
            anchors.verticalCenter: parent.verticalCenter
            spacing: 20

            DashboardIcon {
                source: "assets/icons/safety/seatbelt.svg"
                active: vehicleState.seatbelt
            }
            DashboardIcon {
                source: "assets/icons/safety/airbag.svg"
                active: vehicleState.airbag
            }
            DashboardIcon {
                source: "assets/icons/ev/warning_red.svg"
                active: vehicleState.fault
            }
            DashboardIcon {
                source: "assets/icons/lighting/indicator_right.svg"
                active: vehicleState.rightTurn
            }
        }
    }
}
