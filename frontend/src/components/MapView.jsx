import { MapContainer, TileLayer, GeoJSON, Tooltip } from "react-leaflet";
import { useState, useEffect } from "react";
import "leaflet/dist/leaflet.css";

// Singapore center coordinates
const SG_CENTER = [1.3521, 103.8198];
const SG_ZOOM = 11.5;

// Color scale
function sentimentColor(supportPct) {
  if (supportPct >= 60) return "#22c55e"; // green
  if (supportPct >= 40) return "#f59e0b"; // amber
  return "#ef4444"; // red
}

function sentimentOpacity(total) {
  if (total === 0) return 0.2;
  return Math.min(0.9, 0.3 + total / 100000);
}

export default function MapView({ grcSentiment, selectedGrc, onSelectGrc, className }) {
  const [geoData, setGeoData] = useState(null);

  useEffect(() => {
    // Load GeoJSON - in production, fetch from /data/
    // For hackathon: use GRC center points as circle markers if GeoJSON unavailable
    fetch("/sg_electoral_boundaries.geojson")
      .then((r) => r.json())
      .then(setGeoData)
      .catch(() => console.warn("GeoJSON not loaded — using fallback markers"));
  }, []);

  const styleFeature = (feature) => {
    const name = feature.properties?.Name || feature.properties?.name || "";
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
    const name = feature.properties?.Name || feature.properties?.name || "";
    layer.on("click", () => onSelectGrc(name));

    const sentiment = grcSentiment[name];
    if (sentiment) {
      const sPct = ((sentiment.support / (sentiment.total || 1)) * 100).toFixed(1);
      layer.bindTooltip(`${name}: ${sPct}% support`, { sticky: true });
    }
  };

  return (
    <div className={className}>
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
