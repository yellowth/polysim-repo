import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import { useState, useEffect } from "react";
import "leaflet/dist/leaflet.css";

const SG_CENTER = [1.3521, 103.8198];
const SG_ZOOM = 11.5;

// Exact mapping from GeoJSON ED_DESC (uppercase) to grc_profiles.json keys
const ED_TO_PROFILE = {
  "ALJUNIED": "Aljunied GRC",
  "ANG MO KIO": "Ang Mo Kio GRC",
  "BISHAN-TOA PAYOH": "Bishan-Toa Payoh GRC",
  "BUKIT BATOK": "Bukit Batok SMC",
  "BUKIT PANJANG": "Bukit Panjang SMC",
  "CHUA CHU KANG": "Chua Chu Kang GRC",
  "EAST COAST": "East Coast GRC",
  "HOLLAND-BUKIT TIMAH": "Holland-Bukit Timah GRC",
  "HONG KAH NORTH": "Hong Kah North SMC",
  "HOUGANG": "Hougang SMC",
  "JALAN BESAR": "Jalan Besar GRC",
  "JURONG": "Jurong GRC",
  "KEBUN BARU": "Kebun Baru SMC",
  "MACPHERSON": "MacPherson SMC",
  "MARINE PARADE": "Marine Parade GRC",
  "MARSILING-YEW TEE": "Marsiling-Yew Tee GRC",
  "MARYMOUNT": "Marymount SMC",
  "MOUNTBATTEN": "Mountbatten SMC",
  "NEE SOON": "Nee Soon GRC",
  "PASIR RIS-PUNGGOL": "Pasir Ris-Punggol GRC",
  "PIONEER": "Pioneer SMC",
  "POTONG PASIR": "Potong Pasir SMC",
  "PUNGGOL WEST": "Punggol West SMC",
  "RADIN MAS": "Radin Mas SMC",
  "SEMBAWANG": "Sembawang GRC",
  "SENGKANG": "Sengkang GRC",
  "TAMPINES": "Tampines GRC",
  "TANJONG PAGAR": "Tanjong Pagar GRC",
  "WEST COAST": "West Coast GRC",
  "YIO CHU KANG": "Yio Chu Kang SMC",
  "YUHUA": "Yuhua SMC",
};

function sentimentColor(supportPct) {
  if (supportPct >= 60) return "#22c55e";
  if (supportPct >= 40) return "#f59e0b";
  return "#ef4444";
}

function sentimentOpacity(total) {
  if (total === 0) return 0.2;
  return Math.min(0.9, 0.3 + total / 100000);
}

function getProfileName(feature) {
  const raw = feature.properties?.ED_DESC || feature.properties?.Name || "";
  return ED_TO_PROFILE[raw.toUpperCase()] || raw;
}

export default function MapView({ grcSentiment, selectedGrc, onSelectGrc, className }) {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    fetch("/sg_electoral_boundaries.geojson")
      .then((r) => r.json())
      .then(setGeoData)
      .catch(() => console.warn("GeoJSON not loaded"));
  }, []);

  const styleFeature = (feature) => {
    const name = getProfileName(feature);
    const sentiment = grcSentiment[name];
    const supportPct = sentiment
      ? (sentiment.support / (sentiment.total || 1)) * 100
      : 50;

    return {
      fillColor: sentimentColor(supportPct),
      weight: selectedGrc === name ? 3 : 1,
      color: selectedGrc === name ? "#fff" : "#475569",
      fillOpacity: sentiment ? sentimentOpacity(sentiment.total) : 0.15,
    };
  };

  const onEachFeature = (feature, layer) => {
    const name = getProfileName(feature);
    layer.on("click", () => onSelectGrc(name));

    const sentiment = grcSentiment[name];
    if (sentiment) {
      const sPct = ((sentiment.support / (sentiment.total || 1)) * 100).toFixed(1);
      layer.bindTooltip(`${name}: ${sPct}% support`, { sticky: true });
    } else {
      layer.bindTooltip(name, { sticky: true });
    }
  };

  return (
    <div className={`${className} h-full`}>
      <MapContainer
        center={SG_CENTER}
        zoom={SG_ZOOM}
        className="h-full w-full"
        style={{ background: "#0f172a" }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com">CARTO</a>'
        />
        {geoData && (
          <GeoJSON
            data={geoData}
            style={styleFeature}
            onEachFeature={onEachFeature}
          />
        )}
      </MapContainer>
    </div>
  );
}
