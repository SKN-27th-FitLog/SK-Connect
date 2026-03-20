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

function buildHtml(centerLat, centerLng, level, pinsPayload, pinStylesPayload) {
  const pinsJson = JSON.stringify(pinsPayload);
  const pinStylesJson = JSON.stringify(pinStylesPayload || {});
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
      var pinStyles = ${pinStylesJson};
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
          var p = pins[i];
          
          /* 필터 검사: HTML 내부에서도 렌더링 시 필터 검사를 할 수 있으나
             가장 좋은 방법은 기존에 생성된 마커를 지우고 새로 그리는 것임.
             여기서는 매번 pins가 바뀔 때마다 WebView 전체가 리로드(HTML 재작성)됨. */
          (function (p) {
            var pos = new kakao.maps.LatLng(p.lat, p.lng);
            var pinStyle = pinStyles[p.type] || pinStyles["post"] || { color: "#FF5A5F", iconUrl: "" };

            var content = document.createElement('div');
            content.style.display = 'flex';
            content.style.flexDirection = 'column';
            content.style.alignItems = 'center';
            content.style.cursor = 'pointer';

            var iconImg = document.createElement('img');
            iconImg.src = pinStyle.iconUrl || "https://cdn-icons-png.flaticon.com/512/149/149059.png";
            iconImg.style.width = '32px';
            iconImg.style.height = '32px';
            iconImg.style.backgroundColor = 'white';
            iconImg.style.borderRadius = '50%';
            iconImg.style.border = '2px solid ' + pinStyle.color;
            iconImg.style.boxShadow = '0px 2px 4px rgba(0,0,0,0.3)';
            iconImg.style.objectFit = 'contain';
            iconImg.style.padding = '2px';

            var titleDiv = document.createElement('div');
            titleDiv.style.backgroundColor = pinStyle.color;
            titleDiv.style.color = 'white';
            titleDiv.style.padding = '2px 6px';
            titleDiv.style.borderRadius = '10px';
            titleDiv.style.fontSize = '10px';
            titleDiv.style.fontWeight = 'bold';
            titleDiv.style.marginTop = '4px';
            titleDiv.style.boxShadow = '0px 1px 2px rgba(0,0,0,0.2)';
            titleDiv.style.whiteSpace = 'nowrap';
            titleDiv.innerText = p.title || "";

            content.appendChild(iconImg);
            content.appendChild(titleDiv);

            content.onclick = function() {
              if (window.ReactNativeWebView) {
                window.ReactNativeWebView.postMessage(JSON.stringify({ type: "marker", id: p.id }));
              }
            };

            var customOverlay = new kakao.maps.CustomOverlay({
              position: pos,
              content: content,
              clickable: true,
              yAnchor: 1
            });
            customOverlay.setMap(map);
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
  { center, pins, mapLevel = 3, onMarkerPress, pinStyles },
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

  const getMarkerKey = (p) => {
  if (p.type === "post") {
    return `post-${p.map_id}-${p.post_id}`;
  }
  return `restaurant-${p.map_id}`;
};

const pinsPayload = useMemo(
      () =>
        (pins || []).map((p) => ({
          id: getMarkerKey(p),
          lat: Number(p.latitude) || Number(p.lat) || 0, // [수정] lat 필드 호환성 강화
          lng: Number(p.longitude) || Number(p.lng) || 0, // [수정] lng 필드 호환성 강화
          type: p.type,
          title: p.title || p.name,
        })),
      [pins]
  );

  const html = useMemo(
    () => {
      // pinsPayload가 변경될 때마다 HTML을 새로 생성하여 WebView가 리로드되게 함
      // 이를 통해 지도 상의 핀도 필터링된 배열(pinsPayload)에 맞게 새로 그려짐
      return APP_KEY && center
        ? buildHtml(center.lat, center.lng, mapLevel, pinsPayload, pinStyles)
        : "";
    },
    [center?.lat, center?.lng, mapLevel, pinsPayload, pinStyles]
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
