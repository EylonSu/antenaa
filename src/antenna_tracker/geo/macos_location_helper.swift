import CoreLocation
import Darwin
import Foundation

/// Prints "latitude longitude altitude" once, then exits.
/// Altitude is "nan" when Core Location has no vertical fix.
/// The binary embeds an Info.plist so macOS can show the location prompt.
final class Locator: NSObject, CLLocationManagerDelegate {
    let manager = CLLocationManager()
    var asked = false
    var started = false

    func start() {
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
        fputs("denied\n", stderr)
        exit(2)
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
        print(line)
        fflush(stdout)
        exit(0)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        if (error as NSError).code == CLError.locationUnknown.rawValue {
            return
        }
        fputs("\(error.localizedDescription)\n", stderr)
        exit(1)
    }
}

let locator = Locator()
locator.start()
RunLoop.main.run(until: Date().addingTimeInterval(180))
fputs("timeout\n", stderr)
exit(3)
