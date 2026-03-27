import { MapContainer, TileLayer, GeoJSON, Tooltip } from "react-leaflet";
import { useState, useEffect } from "react";
import "leaflet/dist/leaflet.css";

const SG_CENTER = [1.3521, 103.8198];
const SG_ZOOM = 11.5;

function sentimentColor(supportPct) {
  if (supportPct >= 60) return "#22c55e";
  if (supportPct >= 40) return "#f59e0b";
  return "#ef4444";
}

function sentimentOpacity(total) {
  if (total === 0) return 0.2;
  return Math.min(0.9, 0.3 + total / 100000);
}

export default function MapView({ grcSentiment, selectedGrc, onSelectGrc, className }) {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    fetch("/sg_electoral_boundaries.geojson")
      .then((r) => r.json())
      .then(setGeoData)
      .catch(() => console.warn("GeoJSON not loaded — using fallback markers"));
  }, []);

  // Normalize GeoJSON name (e.g. "ALJUNIED") to match grc_profiles key (e.g. "Aljunied GRC")
  const normalizeGrcName = (rawName) => {
    if (!rawName) return "";
    const titleCase = rawName.replace(/\w\S*/g, (txt) =>
      txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
    );
    // Add GRC suffix if it's a multi-member constituency (most are GRC)
    const smcs = ["Hougang", "Potong Pasir", "Radin Mas", "Bukit Batok", "Bukit Panjang",
                  "Hong Kah North", "Kebun Baru", "Macpherson", "Marymount", "Mountbatten",
                  "Pioneer", "Punggol West", "Yio Chu Kang", "Yuhua"];
    if (smcs.includes(titleCase)) return `${titleCase} SMC`;
    return `${titleCase} GRC`;
  };

  const styleFeature = (feature) => {
    const rawName = feature.properties?.ED_DESC || feature.properties?.Name || "";
    const name = normalizeGrcName(rawName);
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
    const rawName = feature.properties?.ED_DESC || feature.properties?.Name || "";
    const name = normalizeGrcName(rawName);
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
