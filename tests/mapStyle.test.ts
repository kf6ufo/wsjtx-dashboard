import { describe, expect, it } from 'vitest'
import { createExpression } from '@maplibre/maplibre-gl-style-spec'
import type { StyleSpecification, SymbolLayerSpecification } from 'maplibre-gl'
import { englishMapStyle } from '../src/mapStyle'

describe('English station-map labels', () => {
 const original: StyleSpecification = { version: 8, sources: {}, layers: [
  { id: 'places', type: 'symbol', source: 'map', layout: { 'text-field': ['concat', ['get', 'name:latin'], '\n', ['get', 'name:nonlatin']] } },
  { id: 'roads', type: 'symbol', source: 'map', layout: { 'text-field': ['get', 'ref'] } },
 ] }
 it('uses English worldwide, then Latin names, without appending local-script names', () => {
  const style = englishMapStyle(original)
  const field = (style.layers[0] as SymbolLayerSpecification).layout!['text-field']
  const compiled = createExpression(field, 'text-field')
  if (compiled.result !== 'success') throw new Error('Invalid English label expression')
  const label = (properties: Record<string, string>) => compiled.value.evaluate({ zoom: 4 }, { type: 1, properties })
  expect(label({ name_en: 'Japan', 'name:latin': 'Nippon', 'name:nonlatin': '日本' })).toBe('Japan')
  expect(label({ 'name:en': 'Munich', 'name:latin': 'München' })).toBe('Munich')
  expect(label({ 'name:latin': 'Tokyo', name: '東京' })).toBe('Tokyo')
  expect(label({ name: '東京', 'name:nonlatin': '東京' })).toBe('')
  expect(style.layers[1]).toEqual(original.layers[1]) // Highway numbers are not translated.
  expect(original.layers[0]).not.toEqual(style.layers[0]) // Shared source styles stay unchanged.
 })
})
