import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import StationPhoto from '../src/components/StationPhoto.vue'

it('falls back on failed or unsafe photos and recovers when a different station loads', async () => {
 const photo = mount(StationPhoto, { props: { call: 'K1ABC', src: 'https://photos.example.invalid/one.jpg', compact: true } })
 expect(photo.get('img').attributes('referrerpolicy')).toBe('no-referrer')
 await photo.get('img').trigger('error')
 expect(photo.find('img').exists()).toBe(false)
 expect(photo.get('[role="img"]').attributes('aria-label')).toContain('K1ABC')
 await photo.setProps({ call: 'DL1ABC', src: 'https://photos.example.invalid/two.jpg' })
 expect(photo.get('img').attributes('alt')).toContain('DL1ABC')
 await photo.setProps({ src: 'https://user:password@example.invalid/private.jpg' })
 expect(photo.find('img').exists()).toBe(false)
 await photo.setProps({ src: 'javascript:alert(1)' })
 expect(photo.find('img').exists()).toBe(false)
})
