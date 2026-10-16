import AppKit
import CoreLocation
import Foundation

/// Prints one status line, and writes the same line to the path in argv when given.
/// "lat lon alt" on success. "denied", "timeout", or "error" otherwise.
/// Must live in an .app bundle so macOS will show the location prompt.
let outputURL: URL? = CommandLine.arguments.count > 1
    ? URL(fileURLWithPath: CommandLine.arguments[1])
    : nil

func report(_ line: String, _ code: Int32) -> Never {
    if let outputURL {
        try? (line + "\n").write(to: outputURL, atomically: true, encoding: .utf8)
    }
    fputs(line + "\n", stderr)
    fflush(stderr)
    exit(code)
}

final class Locator: NSObject, CLLocationManagerDelegate {
    let manager = CLLocationManager()
    var asked = false
    var started = false

    func start() {
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        app.finishLaunching()
        if #available(macOS 14.0, *) {
            app.activate()
        } else {
            app.activate(ignoringOtherApps: true)
        }
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        manager.delegate = self
        handle(manager.authorizationStatus)
    }

    func handle(_ status: CLAuthorizationStatus) {
        if status == .authorizedAlways {
            begin()
            return
        }
        if status == .notDetermined {
            if !asked {
                asked = true
                manager.requestWhenInUseAuthorization()
            }
            return
        }
        report("denied", 2)
    }

    func begin() {
        if started {
            return
        }
        started = true
        manager.startUpdatingLocation()
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        handle(manager.authorizationStatus)
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last, loc.horizontalAccuracy >= 0 else { return }
        let alt = loc.verticalAccuracy >= 0
            ? String(format: "%.1f", loc.altitude)
            : "nan"
        let line = String(format: "%.6f %.6f", loc.coordinate.latitude, loc.coordinate.longitude) + " " + alt
        report(line, 0)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        if (error as NSError).code == CLError.locationUnknown.rawValue {
            return
        }
        report("error", 1)
    }
}

let locator = Locator()
locator.start()
RunLoop.main.run(until: Date().addingTimeInterval(180))
report("timeout", 3)
