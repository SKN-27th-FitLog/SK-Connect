/**
 * 카카오맵 WebView (JS SDK)
 * - ref: setCenter(lat,lng), zoomIn(), zoomOut()
 * - 환경 변수: EXPO_PUBLIC_KAKAO_MAP_JS_KEY
 */
import React, { useMemo, useRef, useImperativeHandle, forwardRef } from "react";
import { View, Text } from "react-native";
import { WebView } from "react-native-webview";

import { MAP_LEVEL_MIN, MAP_LEVEL_MAX } from "../../config/map";
import mapScreenStyles from "../../styles/map";

const APP_KEY = process.env.EXPO_PUBLIC_KAKAO_MAP_JS_KEY || "";

function buildHtml(centerLat, centerLng, level, pinsPayload) {
  const pinsJson = JSON.stringify(pinsPayload);
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0" />
  <script src="https://dapi.kakao.com/v2/maps/sdk.js?appkey=${APP_KEY}&libraries=services"></script>
  <style>
    html, body { margin: 0; padding: 0; height: 100%; }
    #map { width: 100%; height: 100%; }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    (function () {
      var pins = ${pinsJson};
      var centerLat = ${centerLat};
      var centerLng = ${centerLng};
      var level = ${level};
      function init() {
        if (typeof kakao === "undefined" || !kakao.maps) return;
        var container = document.getElementById("map");
        var options = {
          center: new kakao.maps.LatLng(centerLat, centerLng),
          level: level
        };
        var map = new kakao.maps.Map(container, options);
        window.__kakaoMap = map;
        for (var i = 0; i < pins.length; i++) {
          (function (p) {
            var pos = new kakao.maps.LatLng(p.lat, p.lng);
            var marker = new kakao.maps.Marker({ position: pos });
            marker.setMap(map);
            kakao.maps.event.addListener(marker, "click", function () {
              if (window.ReactNativeWebView) {
                window.ReactNativeWebView.postMessage(JSON.stringify({ type: "marker", id: p.id }));
              }
            });
          })(pins[i]);
        }
      }
      if (document.readyState === "complete") {
        setTimeout(init, 0);
      } else {
        window.onload = function () { setTimeout(init, 100); };
      }
    })();
  </script>
</body>
</html>`;
}

function inject(webRef, code) {
  if (!webRef.current) return;
  webRef.current.injectJavaScript(`try{${code}}catch(e){};true;`);
}

const KakaoMapWebView = forwardRef(function KakaoMapWebView(
  { center, pins, mapLevel = 3, onMarkerPress },
  ref
) {
  const webRef = useRef(null);

  useImperativeHandle(ref, () => ({
    setCenter(lat, lng) {
      inject(
        webRef,
        `if(window.__kakaoMap&&typeof kakao!=="undefined"){window.__kakaoMap.setCenter(new kakao.maps.LatLng(${Number(lat)},${Number(lng)}));}`
      );
    },
    zoomIn() {
      inject(
        webRef,
        `if(window.__kakaoMap&&typeof kakao!=="undefined"){var m=window.__kakaoMap,L=m.getLevel();m.setLevel(Math.max(${MAP_LEVEL_MIN},L-1));}`
      );
    },
    zoomOut() {
      inject(
        webRef,
        `if(window.__kakaoMap&&typeof kakao!=="undefined"){var m=window.__kakaoMap,L=m.getLevel();m.setLevel(Math.min(${MAP_LEVEL_MAX},L+1));}`
      );
    },
  }));

  const pinsPayload = useMemo(
    () => (pins || []).map((p) => ({ id: p.id, lat: Number(p.lat), lng: Number(p.lng) })),
    [pins]
  );

  const html = useMemo(
    () =>
      APP_KEY && center
        ? buildHtml(center.lat, center.lng, mapLevel, pinsPayload)
        : "",
    [center, mapLevel, pinsPayload]
  );

  if (!APP_KEY) {
    return (
      <View style={[mapScreenStyles.mapWebViewContainer, mapScreenStyles.mapWebViewFallback]}>
        <Text style={mapScreenStyles.mapPlaceholderText}>
          카카오맵 JS 키를 설정해 주세요.{"\n"}
          (.env: EXPO_PUBLIC_KAKAO_MAP_JS_KEY)
        </Text>
      </View>
    );
  }

  return (
    <View style={mapScreenStyles.mapWebViewContainer}>
      <WebView
        ref={webRef}
        originWhitelist={["*"]}
        source={{ html }}
        style={mapScreenStyles.mapWebView}
        javaScriptEnabled
        domStorageEnabled
        onMessage={(e) => {
          try {
            const data = JSON.parse(e.nativeEvent.data);
            if (data.type === "marker" && data.id != null && onMarkerPress) {
              onMarkerPress(data.id);
            }
          } catch (_) {}
        }}
      />
    </View>
  );
});

export default KakaoMapWebView;
