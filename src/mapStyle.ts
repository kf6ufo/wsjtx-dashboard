import type { StyleSpecification, ExpressionSpecification } from 'maplibre-gl'

export const MAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty'
export const MAP_ATTRIBUTION = '<a href="https://openfreemap.org/" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> · &copy; <a href="https://www.openmaptiles.org/" target="_blank" rel="noopener noreferrer">OpenMapTiles</a> · Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>'

// OpenMapTiles supplies English names and transliterated Latin names separately.
// Never append the default style's second, local-script label. Road refs stay intact.
export function englishMapStyle(style: StyleSpecification): StyleSpecification {
 const label: ExpressionSpecification = ['coalesce', ['get', 'name_en'], ['get', 'name:en'], ['get', 'name:latin'], '']
 return { ...style, layers: style.layers.map(layer => {
  if (layer.type !== 'symbol' || !layer.layout?.['text-field']) return layer
  const field = layer.layout['text-field']
  if (!/name(?::|_|\b)/.test(JSON.stringify(field))) return layer
  return { ...layer, layout: { ...layer.layout, 'text-field': label } }
 }) }
}
