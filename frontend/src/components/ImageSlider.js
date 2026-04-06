import React from "react";
import { View, Image, ScrollView } from "react-native";

export default function ImageSlider({ images = [] }) {
  if (!images.length) return null;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false}>
      {images.map((uri, i) => (
        <Image key={i} source={{ uri }} style={{ width: 200, height: 150 }} resizeMode="cover" />
      ))}
    </ScrollView>
  );
}
